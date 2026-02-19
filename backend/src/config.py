"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # Neo4j
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"

    # AWS / Bedrock
    aws_region: str = "us-west-2"
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # App
    cors_origins: str = "http://localhost:3000"
    debug: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
