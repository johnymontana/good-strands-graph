"""Chat API routes for the book recommendation agent."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...agents.book_agent import get_book_agent
from ...services.memory_service import get_memory_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message to the agent")
    session_id: str | None = Field(
        default=None, description="Session ID for conversation continuity"
    )


class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent response")
    session_id: str = Field(..., description="Session ID for this conversation")


class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: str | None = None


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=10, ge=1, le=100)


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

        # Invoke the agent
        logger.info(f"Processing chat for session {session_id}")
        result = agent(request.message)
        response_text = str(result)

        # Store assistant response
        await memory_service.add_conversation_message(
            session_id=session_id,
            role="assistant",
            content=response_text,
        )

        return ChatResponse(response=response_text, session_id=session_id)

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
