"""FastAPI application for the Good Strands Graph book recommendation agent."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import chat
from .config import get_settings
from .services.memory_service import get_memory_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting Good Strands Graph...")

    try:
        memory_service = get_memory_service()
        await memory_service.initialize()
        logger.info("Memory service initialized")
    except Exception as e:
        logger.warning(f"Could not initialize memory service: {e}")
        logger.warning("Running without Neo4j memory — some features will be limited")

    yield

    logger.info("Shutting down...")
    try:
        memory_service = get_memory_service()
        await memory_service.close()
    except Exception as e:
        logger.warning(f"Error closing memory service: {e}")


app = FastAPI(
    title="Good Strands Graph",
    description="Agentic book recommendation agent powered by Neo4j and AWS Strands",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "Good Strands Graph",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    return {
        "status": "healthy",
        "version": "0.1.0",
    }
