"""Chat API routes for the book recommendation agent."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...agents.book_agent import get_book_agent
from ...services.memory_service import get_memory_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory cart storage keyed by session_id
_cart_store: dict[str, dict] = {}

# Tool names whose results should be included in the API response
_TOOL_NAMES_TO_EXPOSE = {
    "search_books",
    "get_book_details",
    "get_book_reviews",
    "find_similar_books",
    "get_popular_books",
    "get_books_by_publisher",
    "get_recommended_books",
    "add_to_cart",
    "get_cart",
    "remove_from_cart",
    "checkout",
}


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to the agent")
    session_id: str | None = Field(
        default=None, description="Session ID for conversation continuity"
    )


class ToolResultItem(BaseModel):
    tool_name: str
    tool_use_id: str
    data: Any


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session ID for this conversation")
    tool_results: list[ToolResultItem] = Field(
        default_factory=list, description="Structured tool results for rich rendering"
    )


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)


def extract_tool_results(agent) -> list[ToolResultItem]:
    """Extract tool call results from the agent's conversation messages."""
    tool_results = []

    # Build a map of toolUseId -> tool_name from assistant messages
    tool_use_map: dict[str, str] = {}
    for msg in agent.messages:
        if msg.get("role") == "assistant":
            for block in msg.get("content", []):
                if isinstance(block, dict) and "toolUse" in block:
                    tu = block["toolUse"]
                    tool_use_map[tu["toolUseId"]] = tu["name"]

    # Extract toolResult data from user messages (tool results come back as user role)
    for msg in agent.messages:
        if msg.get("role") == "user":
            for block in msg.get("content", []):
                if isinstance(block, dict) and "toolResult" in block:
                    tr = block["toolResult"]
                    tool_use_id = tr.get("toolUseId", "")
                    tool_name = tool_use_map.get(tool_use_id)

                    if tool_name and tool_name in _TOOL_NAMES_TO_EXPOSE:
                        for content in tr.get("content", []):
                            data = None
                            if isinstance(content, dict):
                                if "json" in content:
                                    data = content["json"]
                                elif "text" in content:
                                    try:
                                        data = json.loads(content["text"])
                                    except (json.JSONDecodeError, TypeError):
                                        pass
                            if data is not None:
                                tool_results.append(
                                    ToolResultItem(
                                        tool_name=tool_name,
                                        tool_use_id=tool_use_id,
                                        data=data,
                                    )
                                )

    return tool_results


@router.post("", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    """Send a message to the book recommendation agent."""
    session_id = request.session_id or str(uuid.uuid4())

    try:
        memory_service = get_memory_service()
        agent = get_book_agent()

        # Store user message
        await memory_service.add_conversation_message(
            session_id=session_id,
            role="user",
            content=request.message,
        )

        # Get or initialize cart for this session
        cart = _cart_store.get(session_id, {})

        # Invoke the agent with cart state
        logger.info(f"Processing chat for session {session_id}")
        result = agent(
            request.message,
            invocation_state={"cart": cart},
        )
        response_text = str(result)

        # Persist updated cart state
        if result.state and isinstance(result.state, dict):
            _cart_store[session_id] = result.state.get("cart", cart)
        else:
            # Cart may have been updated via invocation_state in tool_context
            _cart_store[session_id] = cart

        # Extract structured tool results
        tool_results = extract_tool_results(agent)

        # Store assistant response
        await memory_service.add_conversation_message(
            session_id=session_id,
            role="assistant",
            content=response_text,
        )

        return ChatResponse(
            response=response_text,
            session_id=session_id,
            tool_results=tool_results,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@router.get("/history/{session_id}", response_model=list[ConversationMessage])
async def get_conversation_history(
    session_id: str, limit: int = 50
) -> list[ConversationMessage]:
    """Get conversation history for a session."""
    try:
        memory_service = get_memory_service()
        messages = await memory_service.get_conversation_history(
            session_id=session_id, limit=limit
        )
        return [
            ConversationMessage(
                role=m["role"], content=m["content"], timestamp=m.get("timestamp")
            )
            for m in messages
        ]
    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_conversations(request: SearchRequest) -> list[dict[str, Any]]:
    """Search conversation history semantically."""
    try:
        memory_service = get_memory_service()
        return await memory_service.search_conversations(
            query=request.query, limit=request.limit
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
