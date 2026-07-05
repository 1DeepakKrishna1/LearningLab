import json
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
ENV_FILE = BASE_DIR / ".env"

DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

load_dotenv(ENV_FILE)

SYSTEM_CONFIG_FILE = DATA_DIR / "system_config.json"
GUARDRAILS_FILE = DATA_DIR / "guardrails.json"


def _default_system_config() -> dict:
    return {
        "active_llm": "openai",
        "models": {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
            "google": "gemini-1.5-pro",
            "groq": "llama-3.3-70b-versatile",
        },
        "system_prompt": (
            "You are a helpful, accurate, and friendly AI assistant. "
            "Provide clear, concise, and well-structured responses. "
            "When appropriate, suggest related topics the user might find useful."
        ),
        "context_window": 5,
    }


def _default_guardrails() -> dict:
    return {
        "enabled": True,
        "rules": [
            {
                "id": "no_harmful_content",
                "name": "No Harmful Content",
                "description": "Block requests for harmful, violent, or dangerous content",
                "enabled": True,
                "type": "keyword_block",
                "keywords": ["how to make a bomb", "how to harm", "instructions for violence"],
                "response": "I'm unable to assist with that request as it may involve harmful content.",
            },
            {
                "id": "no_personal_info",
                "name": "No Personal Information Requests",
                "description": "Prevent the AI from soliciting personal information",
                "enabled": True,
                "type": "output_filter",
                "keywords": ["share your credit card", "provide your ssn", "give me your password"],
                "response": "I cannot request personal or sensitive information from users.",
            },
            {
                "id": "professional_tone",
                "name": "Professional Tone",
                "description": "Maintain professional and respectful communication",
                "enabled": True,
                "type": "topic_restriction",
                "keywords": [],
                "response": "Please keep the conversation professional and respectful.",
            },
        ],
    }


def load_system_config() -> dict:
    if not SYSTEM_CONFIG_FILE.exists():
        config = _default_system_config()
        SYSTEM_CONFIG_FILE.write_text(json.dumps(config, indent=2))
        return config
    return json.loads(SYSTEM_CONFIG_FILE.read_text())


def save_system_config(config: dict) -> None:
    SYSTEM_CONFIG_FILE.write_text(json.dumps(config, indent=2))


def load_guardrails() -> dict:
    if not GUARDRAILS_FILE.exists():
        gr = _default_guardrails()
        GUARDRAILS_FILE.write_text(json.dumps(gr, indent=2))
        return gr
    return json.loads(GUARDRAILS_FILE.read_text())


def save_guardrails(guardrails: dict) -> None:
    GUARDRAILS_FILE.write_text(json.dumps(guardrails, indent=2))


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-use-secrets-module")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/conversations.db"

    @staticmethod
    def get_api_key(provider: str) -> str:
        return os.getenv(f"{provider.upper()}_API_KEY", "")

    @staticmethod
    def set_api_key(provider: str, key: str) -> None:
        env_key = f"{provider.upper()}_API_KEY"
        os.environ[env_key] = key
        if not ENV_FILE.exists():
            ENV_FILE.touch()
        set_key(str(ENV_FILE), env_key, key)

    @staticmethod
    def get_all_api_keys() -> dict[str, str]:
        return {
            p: os.getenv(f"{p.upper()}_API_KEY", "")
            for p in ("openai", "anthropic", "google", "groq")
        }


settings = Settings()
