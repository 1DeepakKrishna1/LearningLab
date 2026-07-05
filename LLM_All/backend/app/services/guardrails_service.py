"""Guardrails engine: validates input/output against configured rules."""
from __future__ import annotations

from dataclasses import dataclass

from app.config import load_guardrails


@dataclass
class GuardrailResult:
    blocked: bool
    reason: str
    response: str


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(kw.lower() in lower for kw in keywords if kw)


def check_input(user_message: str) -> GuardrailResult:
    """Check user input against guardrail rules before sending to LLM."""
    config = load_guardrails()
    if not config.get("enabled", True):
        return GuardrailResult(blocked=False, reason="", response="")

    for rule in config.get("rules", []):
        if not rule.get("enabled", True):
            continue
        rule_type = rule.get("type", "")
        if rule_type in ("keyword_block", "topic_restriction"):
            if _matches_keywords(user_message, rule.get("keywords", [])):
                return GuardrailResult(
                    blocked=True,
                    reason=rule["name"],
                    response=rule.get("response", "This request cannot be processed."),
                )

    return GuardrailResult(blocked=False, reason="", response="")


def check_output(ai_response: str) -> GuardrailResult:
    """Check LLM output against guardrail rules before returning to user."""
    config = load_guardrails()
    if not config.get("enabled", True):
        return GuardrailResult(blocked=False, reason="", response="")

    for rule in config.get("rules", []):
        if not rule.get("enabled", True):
            continue
        if rule.get("type") == "output_filter":
            if _matches_keywords(ai_response, rule.get("keywords", [])):
                return GuardrailResult(
                    blocked=True,
                    reason=rule["name"],
                    response=rule.get("response", "The response has been filtered."),
                )

    return GuardrailResult(blocked=False, reason="", response="")
