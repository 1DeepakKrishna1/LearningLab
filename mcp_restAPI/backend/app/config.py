"""Application configuration loaded from environment / .env file."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    Values are read from environment variables, falling back to a local
    ``.env`` file. See ``.env.example`` for documentation of each field.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")

    # Agent
    agent_max_steps: int = Field(default=12, alias="AGENT_MAX_STEPS")
    # NoDecode keeps pydantic-settings from JSON-parsing the raw env value, so a
    # plain comma-separated string reaches the `_split_csv` validator below.
    approval_required_methods: Annotated[list[str], NoDecode] = Field(
        default=["POST", "PUT", "PATCH", "DELETE"],
        alias="APPROVAL_REQUIRED_METHODS",
    )

    # Server
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        alias="CORS_ORIGINS",
    )
    http_timeout: float = Field(default=30.0, alias="HTTP_TIMEOUT")

    @field_validator("approval_required_methods", "cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Allow comma-separated env strings for list fields."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("approval_required_methods", mode="after")
    @classmethod
    def _upper(cls, value: list[str]) -> list[str]:
        return [m.upper() for m in value]


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
