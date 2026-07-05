"""Application configuration, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM (OpenAI)
    openai_api_key: str = ""
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2000

    # Embeddings (OpenAI)
    embedding_model: str = "text-embedding-3-small"

    # Uploads
    max_upload_mb: int = 100  # per-file upload size limit
    max_upload_files: int = 30
    pdf_ocr_max_pages: int = 30  # cap on scanned-PDF pages sent to vision OCR
    pdf_ocr_dpi: int = 150

    # Crawler
    max_crawl_depth: int = 2
    max_pages: int = 200
    crawl_concurrency: int = 8
    request_timeout: float = 20.0
    same_domain_only: bool = True
    respect_robots: bool = True
    user_agent: str = "KnowledgePortalBot/1.0 (+https://example.com)"

    # RAG
    chunk_size: int = 1200
    chunk_overlap: int = 200
    top_k: int = 6

    # Storage / server
    data_dir: str = "./data"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
