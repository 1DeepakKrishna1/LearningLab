"""Unit tests for the unified LLM resolver (Groq + library providers)."""
import pytest

from app import llm


def test_is_groq_explicit():
    assert llm._is_groq("groq", None) is True
    assert llm._is_groq("anthropic", None) is False


def test_is_groq_inferred_from_model():
    assert llm._is_groq("", "llama-3.3-70b-versatile") is True
    assert llm._is_groq("", "groq/mixtral-8x7b-32768") is True
    assert llm._is_groq("", "claude-sonnet-4-6") is False


def test_is_groq_env_only(monkeypatch):
    for k in llm._LIBRARY_KEYS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_dummy")
    assert llm._is_groq("", None) is True
    # If a library key is also present, don't auto-pick Groq.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-dummy")
    assert llm._is_groq("", None) is False


def test_resolve_builds_groq(monkeypatch):
    pytest.importorskip("langchain_groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_dummy")
    model = llm.resolve_chat_model(provider="groq", model="llama-3.3-70b-versatile")
    assert model.__class__.__name__ == "ChatGroq"
    # strips the optional "groq/" prefix
    stripped = llm.resolve_chat_model(provider="groq", model="groq/llama-3.1-8b-instant")
    assert getattr(stripped, "model_name", getattr(stripped, "model", "")).endswith("llama-3.1-8b-instant")
