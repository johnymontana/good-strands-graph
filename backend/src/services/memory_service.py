"""Memory service for Neo4j Agent Memory integration."""

from __future__ import annotations

import logging
from typing import Any

from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.config.settings import (
    EmbeddingConfig,
    EmbeddingProvider,
    Neo4jConfig,
)

from ..config import get_settings

logger = logging.getLogger(__name__)


class BookMemoryService:
    """Service managing conversation memory via Neo4j Agent Memory.

    Provides short-term memory (conversation history) for the book
    recommendation agent, backed by Neo4j.
    """

    def __init__(self) -> None:
        settings = get_settings()
        memory_settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri=settings.neo4j_uri,
                user=settings.neo4j_user,
                password=settings.neo4j_password,
                database=settings.neo4j_database,
            ),
            embedding=EmbeddingConfig(
                provider=EmbeddingProvider.BEDROCK,
                model=settings.bedrock_embedding_model_id,
                aws_region=settings.aws_region,
            ),
        )
        self._client = MemoryClient(memory_settings)
        self._initialized = False

    async def initialize(self) -> None:
        if not self._initialized:
            await self._client.connect()
            self._initialized = True
            logger.info("BookMemoryService initialized")

    async def close(self) -> None:
        await self._client.close()
        self._initialized = False
        logger.info("BookMemoryService closed")

    # ------------------------------------------------------------------
    # Short-term memory (conversation)
    # ------------------------------------------------------------------

    async def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self._client.short_term.add_message(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {},
        )

    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        messages = await self._client.short_term.get_conversation(
            session_id=session_id,
            limit=limit,
        )
        return [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "metadata": m.metadata,
            }
            for m in messages
        ]

    async def search_conversations(
        self,
        query: str,
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        results = await self._client.short_term.search_messages(
            query=query,
            limit=limit,
        )
        return [
            {
                "content": r.content,
                "role": r.role,
                "score": r.metadata.get("similarity") if r.metadata else None,
            }
            for r in results
        ]


# Singleton
_memory_service: BookMemoryService | None = None


def get_memory_service() -> BookMemoryService:
    global _memory_service
    if _memory_service is None:
        _memory_service = BookMemoryService()
    return _memory_service
