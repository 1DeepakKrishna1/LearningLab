"""
Guardrails Framework — Example Usage
=====================================
Demonstrates three integration patterns:
  1. Programmatic setup (no config file)
  2. Config-file driven setup (YAML)
  3. Custom guardrail registration
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Programmatic Setup
# ---------------------------------------------------------------------------

async def example_programmatic() -> None:
    """Build executor in code — ideal for unit tests and microservices."""
    from guardrails.executor.executor import GuardrailExecutor
    from guardrails.input.prompt_injection import AntiPromptInjectionGuardrail
    from guardrails.input.pii_detection import PIIDetectionGuardrail
    from guardrails.input.sql_injection import SQLInjectionGuardrail
    from guardrails.output.redundancy import RedundancyRemovalGuardrail
    from guardrails.output.readability import ReadabilityGuardrail
    from guardrails.models.types import GuardrailConfig
    from guardrails.registry.registry import GuardrailRegistry
    from guardrails.utils.exceptions import PipelineBlockedError
    from guardrails.utils.log_config import setup_logging

    setup_logging(level="INFO", structured=False)

    registry = GuardrailRegistry()

    # ── Input guardrails ────────────────────────────────────────────────────
    #   sequence_id (power of 2) determines which bitmask bit controls it.
    registry.register(
        AntiPromptInjectionGuardrail(
            GuardrailConfig(name="anti_prompt_injection", sequence_id=1)
        )
    )
    registry.register(
        PIIDetectionGuardrail(
            GuardrailConfig(
                name="pii_detection",
                sequence_id=2,
                parameters={"mode": "redact"},
            )
        )
    )
    registry.register(
        SQLInjectionGuardrail(
            GuardrailConfig(name="sql_injection", sequence_id=16)
        )
    )

    # ── Output guardrails ───────────────────────────────────────────────────
    registry.register(
        RedundancyRemovalGuardrail(
            GuardrailConfig(name="redundancy_removal", sequence_id=8)
        )
    )
    registry.register(
        ReadabilityGuardrail(
            GuardrailConfig(name="readability", sequence_id=16)
        )
    )

    # Bitmask: activate injection(1) + pii(2) + sql(16) = 0b10011 = 19
    #          activate redundancy(8) + readability(16)  = 0b11000 = 24
    executor = GuardrailExecutor(
        registry=registry,
        input_mapped_number=19,
        output_mapped_number=24,
        block_on_input_failure=True,
        block_on_output_failure=False,
    )

    # ── Simulated LLM ──────────────────────────────────────────────────────
    async def mock_llm(prompt: str) -> str:
        return (
            "Python is a high-level, general-purpose programming language. "
            "Python is a high-level, general-purpose programming language. "  # intentional duplicate
            "It was created by Guido van Rossum and released in 1991."
        )

    # ── Scenario A: clean input ────────────────────────────────────────────
    print("\n=== Scenario A: Clean input ===")
    ctx = await executor.execute_pipeline(
        "Can you explain what Python is?", llm_invoke=mock_llm
    )
    print(f"Correlation ID : {ctx.correlation_id}")
    print(f"Input passed   : {ctx.input_passed}")
    print(f"Output passed  : {ctx.output_passed}")
    print(f"Final output   : {ctx.final_output}")
    for r in ctx.input_results + ctx.output_results:
        print(f"  [{r.guardrail_name}] {r.status} — {r.message}")

    # ── Scenario B: PII in input ───────────────────────────────────────────
    print("\n=== Scenario B: PII input (redact mode) ===")
    ctx2 = await executor.execute_pipeline(
        "My SSN is 123-45-6789 and email is alice@example.com. Help me.",
        llm_invoke=mock_llm,
    )
    print(f"Sanitized input: {ctx2.sanitized_input}")

    # ── Scenario C: SQL injection — blocked ────────────────────────────────
    print("\n=== Scenario C: SQL injection (blocked) ===")
    try:
        await executor.execute_pipeline(
            "'; DROP TABLE users; --", llm_invoke=mock_llm
        )
    except PipelineBlockedError as e:
        print(f"Pipeline blocked: {e}")


# ---------------------------------------------------------------------------
# 2. Config-file Driven Setup
# ---------------------------------------------------------------------------

async def example_from_config() -> None:
    """Load everything from guardrails.yaml."""
    from guardrails import create_executor, PipelineBlockedError

    config_path = str(Path(__file__).parent.parent / "config" / "guardrails.yaml")
    api_key = os.environ.get("GROQ_API_KEY", "")  # empty → LLM-based checks skipped

    executor = create_executor(config_path=config_path, api_key=api_key)
    print("\n=== Config-file executor registered guardrails ===")
    print(executor.registry.list_all())

    async def stub_llm(prompt: str) -> str:
        return "This is a helpful and clear response to your question."

    ctx = await executor.execute_pipeline("Tell me about pandas.", llm_invoke=stub_llm)
    print(f"Input passed: {ctx.input_passed}, Output passed: {ctx.output_passed}")
    print(f"Final output: {ctx.final_output}")


# ---------------------------------------------------------------------------
# 3. Custom Guardrail — plugging in a new one
# ---------------------------------------------------------------------------

async def example_custom_guardrail() -> None:
    """Shows how easy it is to add a new guardrail."""
    from guardrails.base.guardrail import InputGuardrail
    from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext
    from guardrails.registry.registry import GuardrailRegistry
    from guardrails.executor.executor import GuardrailExecutor

    class WordLimitGuardrail(InputGuardrail):
        """Custom guardrail: reject inputs longer than N words."""

        async def _execute(
            self, content: str, context: PipelineContext
        ) -> GuardrailResult:
            max_words: int = self.config.parameters.get("max_words", 50)
            word_count = len(content.split())
            if word_count > max_words:
                return self._fail_result(
                    score=max_words / word_count,
                    message=f"Input too long: {word_count} words (max {max_words})",
                    flags=["TOO_LONG"],
                )
            return self._pass_result(
                score=1.0,
                message=f"Input length OK: {word_count} words",
            )

    registry = GuardrailRegistry()
    registry.register(
        WordLimitGuardrail(
            GuardrailConfig(
                name="word_limit",
                sequence_id=1,
                parameters={"max_words": 10},
            )
        )
    )
    executor = GuardrailExecutor(
        registry=registry, input_mapped_number=1, block_on_input_failure=True
    )

    from guardrails.utils.exceptions import PipelineBlockedError

    print("\n=== Custom guardrail: word limit ===")
    try:
        await executor.execute_pipeline(
            "This is a very long sentence with way more than ten words in it, sorry."
        )
    except PipelineBlockedError as e:
        print(f"Blocked: {e}")

    ctx = await executor.execute_pipeline("Short input here.")
    print(f"Short input passed: {ctx.input_passed}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(example_programmatic())
    asyncio.run(example_from_config())
    asyncio.run(example_custom_guardrail())
