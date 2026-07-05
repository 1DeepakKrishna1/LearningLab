"""Application configuration.

Settings are sourced from environment variables (``.env``) with sane local
defaults, and merged with JSON configuration files under ``data/config`` so that
non-secret operational settings can be edited without touching code.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository layout:  <repo>/backend/app/core/config.py  ->  <repo>
BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = REPO_ROOT / "data"


class Settings(BaseSettings):
    """Environment-driven settings (secrets + infra)."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "Campaign Management Platform"
    ENV: str = "local"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'campaign.db').as_posix()}"

    # --- Security / JWT ---
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-please-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # --- Rate limiting (per-IP, sliding window) ---
    RATE_LIMIT_REQUESTS: int = 300
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    LOGIN_RATE_LIMIT_REQUESTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # --- Execution engine ---
    EXECUTION_BATCH_SIZE: int = 500
    EXECUTION_MAX_RETRIES: int = 3
    SCHEDULER_POLL_SECONDS: int = 15
    ENABLE_SCHEDULER: bool = True

    # --- Paths ---
    DATA_DIR: Path = DATA_DIR
    BASE_URL: str = "http://localhost:8000"  # used for tracking pixel / click links


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def load_json_config(name: str) -> dict[str, Any]:
    """Load and cache a JSON config file from ``data/config``.

    Args:
        name: file name without extension, e.g. ``"app"`` -> ``data/config/app.json``.
    """
    path = get_settings().DATA_DIR / "config" / f"{name}.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_json_file(relative_path: str) -> Any:
    """Load an arbitrary JSON file relative to the ``data`` directory."""
    path = get_settings().DATA_DIR / relative_path
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


settings = get_settings()
