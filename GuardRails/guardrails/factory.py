"""Factory — build a fully wired GuardrailExecutor from config."""
from __future__ import annotations

import os
from typing import Optional

from guardrails.config.loader import FrameworkConfig, GuardrailGroupConfig, load_config
from guardrails.executor.executor import GuardrailExecutor
from guardrails.llm.client import LLMClient
from guardrails.llm.groq_client import GroqLLMClient
from guardrails.models.types import GuardrailConfig
from guardrails.registry.registry import GuardrailRegistry
from guardrails.utils.exceptions import GuardrailConfigError
from guardrails.utils.log_config import setup_logging

# Input guardrails
from guardrails.input.prompt_injection import AntiPromptInjectionGuardrail
from guardrails.input.pii_detection import PIIDetectionGuardrail
from guardrails.input.toxicity import ToxicityGuardrail
from guardrails.input.relevance import ContextualRelevanceGuardrail
from guardrails.input.sql_injection import SQLInjectionGuardrail
from guardrails.input.intent_alignment import IntentAlignmentGuardrail

# Output guardrails
from guardrails.output.json_validator import JSONValidatorGuardrail
from guardrails.output.schema_compliance import SchemaComplianceGuardrail
from guardrails.output.consistency import LogicalConsistencyGuardrail
from guardrails.output.redundancy import RedundancyRemovalGuardrail
from guardrails.output.readability import ReadabilityGuardrail
from guardrails.output.quality import OutputQualityGuardrail
from guardrails.output.content_filter import ContentFilterGuardrail
from guardrails.output.brand_safety import BrandSafetyGuardrail

_INPUT_GUARDRAIL_CLASSES = {
    "anti_prompt_injection": AntiPromptInjectionGuardrail,
    "pii_detection": PIIDetectionGuardrail,
    "toxicity": ToxicityGuardrail,
    "contextual_relevance": ContextualRelevanceGuardrail,
    "sql_injection": SQLInjectionGuardrail,
    "intent_alignment": IntentAlignmentGuardrail,
}

_OUTPUT_GUARDRAIL_CLASSES = {
    "json_validator": JSONValidatorGuardrail,
    "schema_compliance": SchemaComplianceGuardrail,
    "logical_consistency": LogicalConsistencyGuardrail,
    "redundancy_removal": RedundancyRemovalGuardrail,
    "readability": ReadabilityGuardrail,
    "output_quality": OutputQualityGuardrail,
    "content_filter": ContentFilterGuardrail,
    "brand_safety": BrandSafetyGuardrail,
}


def _build_llm_client(config: FrameworkConfig, api_key: Optional[str]) -> Optional[LLMClient]:
    resolved_key = api_key or os.environ.get(config.llm.api_key_env, "")
    if not resolved_key:
        return None
    if config.llm.provider == "groq":
        return GroqLLMClient(
            api_key=resolved_key,
            model=config.llm.model,
            max_retries=config.llm.max_retries,
            base_timeout=config.llm.timeout_seconds,
        )
    raise GuardrailConfigError(f"Unsupported LLM provider: '{config.llm.provider}'")


def _register_group(
    registry: GuardrailRegistry,
    group: GuardrailGroupConfig,
    class_map: dict,
    llm_client: Optional[LLMClient],
) -> None:
    for gc in group.guardrails:
        cls = class_map.get(gc.name)
        if cls is None:
            raise GuardrailConfigError(
                f"Unknown guardrail name '{gc.name}'. "
                f"Available: {list(class_map.keys())}"
            )
        registry.register(cls(config=gc, llm_client=llm_client))


def create_executor(
    config_path: Optional[str] = None,
    api_key: Optional[str] = None,
    config: Optional[FrameworkConfig] = None,
) -> GuardrailExecutor:
    """Create a fully configured :class:`GuardrailExecutor`.

    Provide either a *config_path* to a YAML/JSON file, or pass an already-
    parsed :class:`FrameworkConfig` directly.

    Args:
        config_path: Path to ``guardrails.yaml`` or ``guardrails.json``.
        api_key: Groq API key.  Falls back to the env-var named in config
                 (``GROQ_API_KEY`` by default).
        config: Pre-built FrameworkConfig (takes precedence over config_path).

    Returns:
        Ready-to-use :class:`GuardrailExecutor`.
    """
    if config is None:
        if config_path is None:
            raise GuardrailConfigError("Provide either config_path or config")
        config = load_config(config_path)

    setup_logging(
        level=config.logging.level,
        structured=config.logging.structured,
        log_file=config.logging.log_file,
    )

    llm_client = _build_llm_client(config, api_key)
    registry = GuardrailRegistry()

    _register_group(registry, config.input, _INPUT_GUARDRAIL_CLASSES, llm_client)
    _register_group(registry, config.output, _OUTPUT_GUARDRAIL_CLASSES, llm_client)

    return GuardrailExecutor(
        registry=registry,
        input_mapped_number=config.input.mapped_number,
        output_mapped_number=config.output.mapped_number,
        block_on_input_failure=config.pipeline.block_on_input_failure,
        block_on_output_failure=config.pipeline.block_on_output_failure,
        max_concurrent=config.pipeline.max_concurrent,
    )
