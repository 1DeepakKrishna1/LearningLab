"""Configuration via pydantic-settings — every field is env-var overridable."""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Redis ──────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    key_prefix: str = Field(default="semcache", alias="KEY_PREFIX")

    # ── Thresholds ─────────────────────────────────────────────────────
    high_th: float = Field(default=0.9, alias="HIGH_TH", ge=0.0, le=1.0)
    low_th: float = Field(default=0.7, alias="LOW_TH", ge=0.0, le=1.0)
    top_k: int = Field(default=5, alias="TOP_K", ge=1)

    # ── TTL ────────────────────────────────────────────────────────────
    default_ttl: int = Field(
        default=3600,
        alias="DEFAULT_TTL",
        ge=0,
        description="Seconds. 0 = no expiry.",
    )

    # ── Embeddings (HuggingFace) ───────────────────────────────────────
    hf_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="HF_MODEL_NAME"
    )
    vector_dim: int = Field(default=384, alias="VECTOR_DIM", ge=1)

    # ── LLM (Groq) ────────────────────────────────────────────────────
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    llm_model: str = Field(default="llama-3.3-70b-versatile", alias="LLM_MODEL")
    llm_max_tokens: int = Field(default=1024, alias="LLM_MAX_TOKENS", ge=1)

    @field_validator("low_th")
    @classmethod
    def low_th_below_high_th(cls, v: float, info) -> float:
        high = info.data.get("high_th", 0.9)
        if v >= high:
            raise ValueError(f"LOW_TH ({v}) must be strictly less than HIGH_TH ({high})")
        return v
