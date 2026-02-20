"""Chat API routes for the book recommendation agent."""

from __future__ import annotations

import ast
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...agents.book_agent import get_book_agent
from ...agents.prompts import BOOK_AGENT_SYSTEM_PROMPT
from ...config import get_settings
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


class ToolCallItem(BaseModel):
    tool_use_id: str
    tool_name: str
    input: dict[str, Any]
    result: Any = None
    status: str = "success"


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session ID for this conversation")
    tool_results: list[ToolResultItem] = Field(
        default_factory=list, description="Structured tool results for rich rendering"
    )
    tool_calls: list[ToolCallItem] = Field(
        default_factory=list, description="All tool calls with inputs and raw results"
    )


class ToolInfo(BaseModel):
    name: str
    description: str
    category: str


class AgentConfigResponse(BaseModel):
    model_id: str
    aws_region: str
    system_prompt: str
    tools: list[ToolInfo]


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)


def _parse_text_value(text: str) -> Any:
    """Parse a text value that may be JSON or Python repr (single-quoted dicts/lists)."""
    # Try JSON first
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # Strands SDK often returns Python repr with single quotes — use ast.literal_eval
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        pass
    return text


def _extract_result_data(tr: dict) -> Any:
    """Extract data from a toolResult block, handling various Strands SDK formats."""
    raw_content = tr.get("content", [])

    # Format 1: content is a list of {json: ...} or {text: ...} blocks
    for content in raw_content:
        if isinstance(content, dict):
            if "json" in content:
                return content["json"]
            if "text" in content:
                return _parse_text_value(content["text"])

    # Format 2: content itself is a string (some Strands versions)
    if isinstance(raw_content, str):
        return _parse_text_value(raw_content)

    # Format 3: content is a list with a single string element
    if raw_content and isinstance(raw_content[0], str):
        return _parse_text_value(raw_content[0])

    return None


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

    logger.info("extract_tool_results: tool_use_map keys=%s", list(tool_use_map.values()))

    # Extract toolResult data from user messages (tool results come back as user role)
    for msg in agent.messages:
        if msg.get("role") == "user":
            for block in msg.get("content", []):
                if isinstance(block, dict) and "toolResult" in block:
                    tr = block["toolResult"]
                    tool_use_id = tr.get("toolUseId", "")
                    tool_name = tool_use_map.get(tool_use_id)

                    logger.info(
                        "extract_tool_results: tool=%s, content_type=%s, content_keys=%s, content_preview=%s",
                        tool_name,
                        type(tr.get("content")).__name__,
                        [type(c).__name__ for c in tr.get("content", [])] if isinstance(tr.get("content"), list) else "N/A",
                        str(tr.get("content", ""))[:300],
                    )

                    if tool_name and tool_name in _TOOL_NAMES_TO_EXPOSE:
                        data = _extract_result_data(tr)
                        if data is not None:
                            tool_results.append(
                                ToolResultItem(
                                    tool_name=tool_name,
                                    tool_use_id=tool_use_id,
                                    data=data,
                                )
                            )

    logger.info("extract_tool_results: found %d results", len(tool_results))
    return tool_results


def extract_tool_calls(agent) -> list[ToolCallItem]:
    """Extract all tool calls with their inputs and results from agent messages."""
    # Build map: toolUseId -> {name, input} from assistant messages
    tool_use_info: dict[str, dict[str, Any]] = {}
    for msg in agent.messages:
        if msg.get("role") == "assistant":
            for block in msg.get("content", []):
                if isinstance(block, dict) and "toolUse" in block:
                    tu = block["toolUse"]
                    tool_use_info[tu["toolUseId"]] = {
                        "name": tu["name"],
                        "input": tu.get("input", {}),
                    }

    # Match with toolResult from user messages
    tool_calls = []
    for msg in agent.messages:
        if msg.get("role") == "user":
            for block in msg.get("content", []):
                if isinstance(block, dict) and "toolResult" in block:
                    tr = block["toolResult"]
                    tool_use_id = tr.get("toolUseId", "")
                    info = tool_use_info.get(tool_use_id)
                    if not info:
                        continue

                    status = tr.get("status", "success")
                    result_data = _extract_result_data(tr)

                    tool_calls.append(
                        ToolCallItem(
                            tool_use_id=tool_use_id,
                            tool_name=info["name"],
                            input=info["input"],
                            result=result_data,
                            status=status,
                        )
                    )

    return tool_calls


# Tool metadata for the /config endpoint
_TOOL_METADATA: list[dict[str, str]] = [
    {"name": "search_books", "description": "Search books by title, description, or semantic meaning", "category": "book_discovery"},
    {"name": "get_book_details", "description": "Get full details for a specific book including publisher and review summary", "category": "book_discovery"},
    {"name": "get_book_reviews", "description": "Get reviews for a specific book", "category": "book_discovery"},
    {"name": "find_similar_books", "description": "Find books similar to a given book using embedding-based similarity", "category": "book_discovery"},
    {"name": "get_popular_books", "description": "Get the most popular books sorted by number of ratings", "category": "book_discovery"},
    {"name": "get_books_by_publisher", "description": "Get books by a specific publisher", "category": "book_discovery"},
    {"name": "get_recommended_books", "description": "Get book recommendations based on collaborative filtering", "category": "book_discovery"},
    {"name": "add_to_cart", "description": "Add a book to the shopping cart", "category": "commerce"},
    {"name": "get_cart", "description": "View the current shopping cart", "category": "commerce"},
    {"name": "remove_from_cart", "description": "Remove a book from the shopping cart", "category": "commerce"},
    {"name": "checkout", "description": "Complete the purchase (simulated)", "category": "commerce"},
    {"name": "search_context", "description": "Search memory for relevant context from past conversations", "category": "memory"},
    {"name": "add_memory", "description": "Save important information to memory", "category": "memory"},
    {"name": "get_user_preferences", "description": "Retrieve known user preferences", "category": "memory"},
    {"name": "get_entity_graph", "description": "Explore relationship networks around entities", "category": "memory"},
]


@router.get("/config", response_model=AgentConfigResponse)
async def get_agent_config() -> AgentConfigResponse:
    """Get agent configuration including system prompt, model info, and tool list."""
    settings = get_settings()
    return AgentConfigResponse(
        model_id=settings.bedrock_model_id,
        aws_region=settings.aws_region,
        system_prompt=BOOK_AGENT_SYSTEM_PROMPT,
        tools=[ToolInfo(**t) for t in _TOOL_METADATA],
    )


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

        # Extract structured tool results and raw tool calls
        tool_results = extract_tool_results(agent)
        tool_calls = extract_tool_calls(agent)

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
            tool_calls=tool_calls,
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
