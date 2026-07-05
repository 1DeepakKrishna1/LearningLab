"""YAML/JSON configuration loader for the guardrails framework."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardrails.models.types import GuardrailConfig
from guardrails.utils.exceptions import GuardrailConfigError


@dataclass
class LLMSettings:
    provider: str = "groq"
    model: str = "llama3-8b-8192"
    api_key_env: str = "GROQ_API_KEY"
    max_retries: int = 3
    timeout_seconds: float = 10.0


@dataclass
class PipelineSettings:
    block_on_input_failure: bool = True
    block_on_output_failure: bool = False
    max_concurrent: int = 4


@dataclass
class LoggingSettings:
    level: str = "INFO"
    structured: bool = True
    log_file: Optional[str] = None


@dataclass
class GuardrailGroupConfig:
    mapped_number: int
    guardrails: List[GuardrailConfig] = field(default_factory=list)


@dataclass
class FrameworkConfig:
    input: GuardrailGroupConfig = field(
        default_factory=lambda: GuardrailGroupConfig(mapped_number=0xFFFF)
    )
    output: GuardrailGroupConfig = field(
        default_factory=lambda: GuardrailGroupConfig(mapped_number=0xFFFF)
    )
    llm: LLMSettings = field(default_factory=LLMSettings)
    pipeline: PipelineSettings = field(default_factory=PipelineSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _parse_guardrail_config(raw: Dict[str, Any]) -> GuardrailConfig:
    return GuardrailConfig(
        name=raw["name"],
        sequence_id=int(raw["sequence_id"]),
        enabled=bool(raw.get("enabled", True)),
        threshold=float(raw.get("threshold", 0.5)),
        fail_on_error=bool(raw.get("fail_on_error", False)),
        timeout_seconds=float(raw.get("timeout_seconds", 5.0)),
        parameters=dict(raw.get("parameters") or {}),
    )


def _parse_group(raw: Dict[str, Any]) -> GuardrailGroupConfig:
    return GuardrailGroupConfig(
        mapped_number=int(raw.get("mapped_number", 0xFFFF)),
        guardrails=[_parse_guardrail_config(g) for g in raw.get("guardrails", [])],
    )


def _parse_framework_config(data: Dict[str, Any]) -> FrameworkConfig:
    gr = data.get("guardrails", {})
    llm_raw = data.get("llm", {})
    pipe_raw = data.get("pipeline", {})
    log_raw = data.get("logging", {})

    return FrameworkConfig(
        input=_parse_group(gr.get("input", {})),
        output=_parse_group(gr.get("output", {})),
        llm=LLMSettings(
            provider=llm_raw.get("provider", "groq"),
            model=llm_raw.get("model", "llama3-8b-8192"),
            api_key_env=llm_raw.get("api_key_env", "GROQ_API_KEY"),
            max_retries=int(llm_raw.get("max_retries", 3)),
            timeout_seconds=float(llm_raw.get("timeout_seconds", 10.0)),
        ),
        pipeline=PipelineSettings(
            block_on_input_failure=bool(pipe_raw.get("block_on_input_failure", True)),
            block_on_output_failure=bool(pipe_raw.get("block_on_output_failure", False)),
            max_concurrent=int(pipe_raw.get("max_concurrent", 4)),
        ),
        logging=LoggingSettings(
            level=str(log_raw.get("level", "INFO")),
            structured=bool(log_raw.get("structured", True)),
            log_file=log_raw.get("log_file"),
        ),
    )


def load_config(path: str) -> FrameworkConfig:
    """Load a YAML or JSON config file and return a :class:`FrameworkConfig`."""
    file_path = Path(path)
    if not file_path.exists():
        raise GuardrailConfigError(f"Config file not found: {path}")

    suffix = file_path.suffix.lower()
    with open(file_path, "r", encoding="utf-8") as fh:
        raw_text = fh.read()

    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
            data: Dict[str, Any] = yaml.safe_load(raw_text) or {}
        except ImportError as exc:
            raise GuardrailConfigError(
                "PyYAML is required to load YAML config files. "
                "Install it with: pip install pyyaml"
            ) from exc
    elif suffix == ".json":
        data = json.loads(raw_text)
    else:
        raise GuardrailConfigError(
            f"Unsupported config file format: {suffix}. Use .yaml or .json"
        )

    return _parse_framework_config(data)
