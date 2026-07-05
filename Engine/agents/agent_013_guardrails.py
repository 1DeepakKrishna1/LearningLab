"""agent-013 – Guardrails Agent."""

import re
from typing import Any, Dict, List

from agents._base_impl import AgentMixin
from core.registry import Registry

# Simple PII patterns (for demo purposes only)
_PII_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # email
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),                     # phone
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                                  # SSN
]

_TOXIC_KEYWORDS = {"hate", "violence", "abuse", "harmful"}


def _check_pii(text: str) -> List[str]:
    found = []
    for p in _PII_PATTERNS:
        if p.search(text):
            found.append(p.pattern)
    return found


def _redact_pii(text: str) -> str:
    for p in _PII_PATTERNS:
        text = p.sub("[REDACTED]", text)
    return text


def _check_toxicity(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _TOXIC_KEYWORDS)


class GuardrailsAgent(AgentMixin):
    @property
    def agent_id(self) -> str:
        return "agent-013"

    def name(self) -> str:
        return "Guardrails Agent"

    def description(self) -> str:
        return "Validates and sanitizes inputs/outputs against safety rules, PII detection, and schema constraints"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        cfg = state.get("current_node_config", {}).get("properties", {})
        check_pii = cfg.get("check_pii", True)
        check_toxicity = cfg.get("check_toxicity", True)
        block_on_violation = cfg.get("block_on_violation", True)
        redact_pii = cfg.get("redact_pii", True)
        max_length = int(cfg.get("max_content_length", 4096))

        content = str(state.get("current_data", {}))
        violations: List[str] = []

        # Length check
        if len(content) > max_length:
            violations.append(f"content_length_exceeded ({len(content)} > {max_length})")

        # PII check
        pii_found = _check_pii(content) if check_pii else []
        if pii_found:
            violations.append(f"pii_detected: {len(pii_found)} pattern(s)")
            if redact_pii:
                # Redact string values in current_data
                for k, v in state["current_data"].items():
                    if isinstance(v, str):
                        state["current_data"][k] = _redact_pii(v)

        # Toxicity check
        is_toxic = _check_toxicity(content) if check_toxicity else False
        if is_toxic:
            violations.append("toxicity_detected")

        passed = len(violations) == 0
        if not passed and block_on_violation:
            state["status"] = "failed"
            state["error"] = f"Guardrails violation: {', '.join(violations)}"

        state["current_data"].update(
            {
                "guardrails_passed": passed,
                "guardrails_violations": violations,
                "pii_patterns_found": len(pii_found),
                "toxicity_detected": is_toxic,
                "content_redacted": bool(pii_found and redact_pii),
            }
        )
        return state


Registry.register_agent(GuardrailsAgent())
