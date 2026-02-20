"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

# Load .env: backend/.env first (same as load_data), then project root so one .env at root works too
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_ROOT.parent
load_dotenv(_BACKEND_ROOT / ".env")
load_dotenv(_PROJECT_ROOT / ".env")  # overlay so project root .env is used if present
_DOTENV_PATH = _PROJECT_ROOT / ".env"  # Pydantic reads from project root for consistency


class Settings(BaseSettings):
    # Neo4j — accept NEO4J_USER or NEO4J_USERNAME (same as load_data pattern)
    neo4j_uri: str = "neo4j://localhost:7687"
    neo4j_user: str = Field(
        default="neo4j",
        validation_alias=AliasChoices("neo4j_user", "neo4j_username"),
    )
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"

    # AWS / Bedrock
    aws_region: str = "us-west-2"
    bedrock_model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"

    # App (allow both localhost and 127.0.0.1 so CORS preflight succeeds from either)
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    debug: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def bedrock_model_id_for_invocation(self) -> str:
        """Use inference profile ID for Converse/ConverseStream (required for on-demand)."""
        mid = self.bedrock_model_id.strip()
        if mid.startswith("anthropic.") and not mid.startswith("us."):
            return f"us.{mid}"
        return mid

    model_config = {
        "env_file": str(_DOTENV_PATH),
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # project .env may have other tools' vars (e.g. aws_bearer_token_bedrock)
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
