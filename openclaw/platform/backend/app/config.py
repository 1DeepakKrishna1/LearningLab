"""Application configuration.

All runtime behaviour is configuration-driven. Settings are loaded (in order of
precedence) from: explicit constructor args → environment variables → a `.env`
file → the defaults declared here. Paths are resolved to absolute at load time so
the rest of the app never has to reason about the current working directory.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo layout anchors:  <repo>/platform/backend/app/config.py
_BACKEND_DIR = Path(__file__).resolve().parent.parent          # .../platform/backend
_PLATFORM_DIR = _BACKEND_DIR.parent                            # .../platform
_REPO_ROOT = _PLATFORM_DIR.parent                              # .../openclaw


class Settings(BaseSettings):
    """Typed, validated application settings."""

    model_config = SettingsConfigDict(
        env_prefix="CLAWFLOW_",
        env_file=str(_BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "ClawFlow"
    env: Literal["development", "staging", "production"] = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    # --- Storage ---
    data_dir: Path = _BACKEND_DIR / "data"
    storage_backend: Literal["json"] = "json"

    # --- Tool library ---
    tool_library_path: Path = _REPO_ROOT / "agents_tools_library" / "library"
    tool_library_pythonpath: Path = _REPO_ROOT / "agents_tools_library"

    # --- Security ---
    jwt_secret: str = "change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    bootstrap_admin_email: str = "admin@clawflow.local"
    bootstrap_admin_password: str = "admin123"

    # --- Agent runtime / LLM ---
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-sonnet-4-6"

    # --- Engine ---
    max_parallel_nodes: int = 8
    default_node_timeout: int = 300
    default_max_retries: int = 2

    # --- Messaging ---
    messaging_provider: Literal["console", "meta", "twilio"] = "console"

    # --- Resolved at load (not from env) ---
    @field_validator("data_dir", "tool_library_path", "tool_library_pythonpath", mode="after")
    @classmethod
    def _resolve(cls, value: Path) -> Path:
        return value if value.is_absolute() else (_BACKEND_DIR / value).resolve()

    def ensure_tool_library_importable(self) -> None:
        """Put the tool-library root on sys.path so `library.tools.*` imports work."""
        p = str(self.tool_library_pythonpath)
        if p not in sys.path:
            sys.path.insert(0, p)


@lru_cache
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()
