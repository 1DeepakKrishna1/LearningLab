"""Secure configuration and secrets management."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AppSettings(BaseSettings):
    """Validated application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # GroQ
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "llama3-70b-8192"
    groq_temperature: float = 0.1
    groq_max_tokens: int = 4096

    # Google Drive
    gdrive_credentials_file: str = "config/gdrive_credentials.json"
    gdrive_token_file: str = "config/gdrive_token.json"
    gdrive_folder_id: str = ""

    # SharePoint
    sharepoint_tenant_id: str = ""
    sharepoint_client_id: str = ""
    sharepoint_client_secret: SecretStr = SecretStr("")
    sharepoint_site_url: str = ""
    sharepoint_drive_id: str = ""

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"

    # Pipeline
    input_dir: str = "./input"
    output_dir: str = "./output"
    batch_size: int = 10
    max_workers: int = 4
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Metrics
    metrics_port: int = 8000
    enable_metrics: bool = True


class SecureConfig:
    """Merges YAML config with environment-validated secrets."""

    def __init__(self, config_path: str = "config/config.yaml") -> None:
        load_dotenv(override=False)
        self.settings = AppSettings()
        self._yaml: dict[str, Any] = self._load_yaml(config_path)

    @staticmethod
    def _load_yaml(path: str) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            logger.warning("config_file_not_found", path=path)
            return {}
        with p.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def get(self, *keys: str, default: Any = None) -> Any:
        """Dot-path access into YAML config, e.g. get('pipeline', 'batch_size')."""
        node: Any = self._yaml
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
        return node

    def get_groq_api_key(self) -> str:
        key = self.settings.groq_api_key.get_secret_value()
        if not key:
            raise ValueError("GROQ_API_KEY is not set. Please configure your .env file.")
        return key

    def get_sharepoint_secret(self) -> str:
        return self.settings.sharepoint_client_secret.get_secret_value()


@lru_cache(maxsize=1)
def get_config(config_path: str = "config/config.yaml") -> SecureConfig:
    """Return a singleton SecureConfig instance."""
    return SecureConfig(config_path)
