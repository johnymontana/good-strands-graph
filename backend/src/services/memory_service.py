"""Memory service for Neo4j Agent Memory integration."""

from __future__ import annotations

import logging
import os
from typing import Any

from pydantic import SecretStr

from neo4j_agent_memory import MemoryClient, MemorySettings
from neo4j_agent_memory.config.settings import (
    EmbeddingConfig,
    EmbeddingProvider,
    Neo4jConfig,
)

from ..config import get_settings

logger = logging.getLogger(__name__)


def _neo4j_env() -> tuple[str, str, str, str]:
    """Neo4j credentials from os.environ (same source as load_data after config load_dotenv)."""
    uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
    user = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD") or os.environ.get("NEO4J_PWD", "password")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    return uri, user, password, database


class BookMemoryService:
    """Service managing conversation memory via Neo4j Agent Memory.

    Provides short-term memory (conversation history) for the book
    recommendation agent, backed by Neo4j.
    """

    def __init__(self) -> None:
        uri, user, password, database = _neo4j_env()
        # Log what we're using (no secrets) so you can confirm we read the same .env as load_data
        logger.info(
            "Neo4j memory: uri=%s, user=%s, database=%s, password_len=%d",
            uri.split("//")[-1].split("/")[0] if "//" in uri else "(redacted)",
            user,
            database,
            len(password) if password else 0,
        )
        settings = get_settings()
        memory_settings = MemorySettings(
            neo4j=Neo4jConfig(
                uri=uri,
                username=user,
                password=SecretStr(password),
                database=database,
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
