# Guardrails Framework — Summary

## Overview

A production-grade, reusable Python framework that wraps any LLM call with configurable
**Input Guardrails** (pre-LLM) and **Output Guardrails** (post-LLM).  
Activation is controlled by a **bitmask**, making it trivial to turn individual checks
on or off without touching code.

---

## Bitmask Activation

Each guardrail has a unique `sequence_id` that is a power of 2 (1, 2, 4, 8, …).  
A `mapped_number` integer acts as a bitmask: a guardrail runs **only when its bit is set**.

```
mapped_number & sequence_id != 0  →  guardrail executes
mapped_number & sequence_id == 0  →  guardrail is skipped
```

**Example**

| Guardrail              | sequence_id | mapped_number = 19 (0b010011) | Active? |
|------------------------|-------------|-------------------------------|---------|
| Anti-Prompt Injection  | 1           | 19 & 1 = 1                    | ✅ Yes  |
| PII Detection          | 2           | 19 & 2 = 2                    | ✅ Yes  |
| Toxicity               | 4           | 19 & 4 = 0                    | ❌ No   |
| Contextual Relevance   | 8           | 19 & 8 = 0                    | ❌ No   |
| SQL Injection          | 16          | 19 & 16 = 16                  | ✅ Yes  |
| Intent Alignment       | 32          | 19 & 32 = 0                   | ❌ No   |

---

## Folder Structure

```
guardrails-framework/
│
├── guardrails/                     # Main package
│   ├── __init__.py                 # Public API surface
│   ├── factory.py                  # create_executor() — one-line setup
│   │
│   ├── models/
│   │   └── types.py                # GuardrailResult, PipelineContext, GuardrailConfig
│   │
│   ├── base/
│   │   └── guardrail.py            # BaseGuardrail, InputGuardrail, OutputGuardrail
│   │
│   ├── llm/
│   │   ├── client.py               # LLMClient (abstract interface)
│   │   └── groq_client.py          # GroqLLMClient (httpx async + retry)
│   │
│   ├── registry/
│   │   └── registry.py             # GuardrailRegistry — register & discover
│   │
│   ├── executor/
│   │   └── executor.py             # GuardrailExecutor — pipeline orchestration
│   │
│   ├── input/                      # Pre-LLM guardrails
│   │   ├── prompt_injection.py     # seq_id=1   Anti-Prompt Injection Defense
│   │   ├── pii_detection.py        # seq_id=2   Sensitive Data / PII Screening
│   │   ├── toxicity.py             # seq_id=4   Language Toxicity Detection
│   │   ├── relevance.py            # seq_id=8   Contextual Relevance Check
│   │   ├── sql_injection.py        # seq_id=16  SQL Injection Prevention
│   │   └── intent_alignment.py     # seq_id=32  Intent Alignment Verification
│   │
│   ├── output/                     # Post-LLM guardrails
│   │   ├── json_validator.py       # seq_id=1   Structured Data / JSON Validator
│   │   ├── schema_compliance.py    # seq_id=2   API Schema Compliance Checker
│   │   ├── consistency.py          # seq_id=4   Logical Consistency Checker
│   │   ├── redundancy.py           # seq_id=8   Redundancy Removal
│   │   ├── readability.py          # seq_id=16  Complexity & Readability Scoring
│   │   ├── quality.py              # seq_id=32  Output Quality Assessment
│   │   ├── content_filter.py       # seq_id=64  Inappropriate Content Filter
│   │   └── brand_safety.py         # seq_id=128 Competitor Shield & Brand Safety
│   │
│   ├── config/
│   │   └── loader.py               # YAML/JSON → FrameworkConfig dataclasses
│   │
│   └── utils/
│       ├── exceptions.py           # PipelineBlockedError, LLMClientError, …
│       └── log_config.py           # Structured JSON logging with correlation IDs
│
├── config/
│   └── guardrails.yaml             # Reference configuration (all guardrails)
│
├── tests/
│   ├── conftest.py                 # Shared fixtures (mock LLM, contexts)
│   ├── test_bitmask.py             # Bitmask logic & registry tests (19 tests)
│   ├── test_input_guardrails.py    # Per-guardrail unit tests (17 tests)
│   ├── test_output_guardrails.py   # Per-guardrail unit tests (16 tests)
│   └── test_pipeline.py            # End-to-end pipeline tests (18 tests)
│
├── examples/
│   └── example_usage.py            # 3 patterns: programmatic, config-file, custom
│
├── requirements.txt
└── pytest.ini
```

---

## Core Components

### `GuardrailResult`
Every guardrail returns this structured result.

| Field              | Type              | Description                              |
|--------------------|-------------------|------------------------------------------|
| `guardrail_name`   | `str`             | Human-readable name                      |
| `status`           | `GuardrailStatus` | `pass` / `fail` / `skip` / `error`       |
| `score`            | `float` 0–1       | Confidence / quality score (1.0 = best)  |
| `message`          | `str`             | Human-readable explanation               |
| `flags`            | `list[str]`       | Machine-readable violation labels        |
| `modified_content` | `str \| None`     | Sanitised content to pass forward        |
| `duration_ms`      | `float`           | Execution time                           |

### `PipelineContext`
Carries state through the entire pipeline.

| Field             | Description                                          |
|-------------------|------------------------------------------------------|
| `correlation_id`  | UUID for distributed tracing / log correlation       |
| `original_input`  | Raw user prompt                                      |
| `sanitized_input` | Modified input (e.g. PII redacted)                   |
| `llm_response`    | Raw LLM output                                       |
| `final_output`    | Post-output-guardrail text                           |
| `input_results`   | All input guardrail results                          |
| `output_results`  | All output guardrail results                         |
| `metadata`        | Arbitrary dict for guardrail-specific data           |

---

## Input Guardrails

| # | Name                       | seq_id | Technique              | Modifies Input? |
|---|----------------------------|--------|------------------------|-----------------|
| 1 | Anti-Prompt Injection      | 1      | Regex patterns          | Optional redact |
| 2 | PII Detection              | 2      | Regex (email, SSN, CC…) | Yes (redact)    |
| 3 | Language Toxicity          | 4      | Regex + optional LLM    | No              |
| 4 | Contextual Relevance       | 8      | Keyword / LLM           | No              |
| 5 | SQL Injection Prevention   | 16     | Regex patterns          | No              |
| 6 | Intent Alignment           | 32     | LLM (Groq)              | No              |

---

## Output Guardrails

| # | Name                       | seq_id | Technique              | Modifies Output? |
|---|----------------------------|--------|------------------------|------------------|
| 1 | JSON Validator             | 1      | `json.loads`            | No               |
| 2 | API Schema Compliance      | 2      | `jsonschema`            | No               |
| 3 | Logical Consistency        | 4      | LLM (Groq)              | No               |
| 4 | Redundancy Removal         | 8      | Jaccard similarity      | Yes (dedup)      |
| 5 | Readability Scoring        | 16     | Flesch Reading Ease     | No               |
| 6 | Output Quality Assessment  | 32     | LLM (Groq)              | No               |
| 7 | Inappropriate Content      | 64     | Regex patterns          | No               |
| 8 | Competitor / Brand Safety  | 128    | Regex (configurable)    | No               |

---

## LLM Integration

```
LLMClient (abstract)
    └── GroqLLMClient
            ├── httpx.AsyncClient (async HTTP)
            ├── Exponential-backoff retry (configurable max_retries)
            ├── Per-request timeout (asyncio.wait_for)
            └── Rate-limit handling (Retry-After header)
```

LLM-dependent guardrails (relevance, intent, consistency, quality) **gracefully skip**
(`status=SKIP`) when no LLM client is configured, so the framework works without an API
key for purely pattern-based checks.

---

## Pipeline Execution Flow

```
User Input
    │
    ▼
┌─────────────────────────────────┐
│   Input Guardrails (sequential) │  ← each may sanitise content for the next
│   controlled by input_mapped_number│
└─────────────────────────────────┘
    │ pass          │ fail + block_on_input_failure=True
    ▼               └──► PipelineBlockedError
┌─────────────────┐
│   LLM Invocation│  ← receives sanitised input
└─────────────────┘
    │
    ▼
┌──────────────────────────────────┐
│   Output Guardrails (sequential) │  ← each may refine the output
│   controlled by output_mapped_number│
└──────────────────────────────────┘
    │
    ▼
PipelineContext.final_output
```

---

## Quickstart

### Install
```bash
pip install -r requirements.txt
```

### Minimal programmatic usage
```python
import asyncio
from guardrails.executor.executor import GuardrailExecutor
from guardrails.input.prompt_injection import AntiPromptInjectionGuardrail
from guardrails.input.pii_detection import PIIDetectionGuardrail
from guardrails.models.types import GuardrailConfig
from guardrails.registry.registry import GuardrailRegistry

registry = GuardrailRegistry()
registry.register(AntiPromptInjectionGuardrail(GuardrailConfig("injection", sequence_id=1)))
registry.register(PIIDetectionGuardrail(GuardrailConfig("pii", sequence_id=2,
                                         parameters={"mode": "redact"})))

executor = GuardrailExecutor(registry, input_mapped_number=3)  # bits 1+2

async def run():
    ctx = await executor.execute_pipeline(
        "My email is alice@example.com. What is Python?",
        llm_invoke=lambda p: asyncio.sleep(0, "Python is a programming language."),
    )
    print(ctx.final_output)
    print(ctx.sanitized_input)  # email redacted

asyncio.run(run())
```

### Config-file driven (one line)
```python
from guardrails import create_executor

executor = create_executor("config/guardrails.yaml", api_key="gsk_...")
ctx = await executor.execute_pipeline(user_prompt, llm_invoke=my_llm)
```

---

## Adding a New Guardrail

```python
from guardrails.base.guardrail import InputGuardrail   # or OutputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

class WordLimitGuardrail(InputGuardrail):
    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        max_words = self.config.parameters.get("max_words", 100)
        count = len(content.split())
        if count > max_words:
            return self._fail_result(
                score=max_words / count,
                message=f"Too long: {count} words (max {max_words})",
                flags=["TOO_LONG"],
            )
        return self._pass_result(score=1.0, message=f"{count} words — OK")

# Register with any power-of-2 sequence_id not already in use
registry.register(WordLimitGuardrail(GuardrailConfig("word_limit", sequence_id=64)))
```

**That's all that's required.** The framework handles timing, logging, error capture,
bitmask activation, and pipeline chaining automatically.

---

## Extending the LLM Provider

```python
from guardrails.llm.client import LLMClient, LLMMessage, LLMResponse

class OpenAIClient(LLMClient):
    async def complete(self, messages, *, temperature=0.0, max_tokens=512, timeout=10.0):
        # call OpenAI API here …
        return LLMResponse(content="...", model="gpt-4o")

    async def health_check(self) -> bool:
        return True  # ping /models endpoint
```

Pass the instance as `llm_client=` when constructing guardrails, or wire it through
`create_executor` by subclassing `GroqLLMClient` / modifying `factory.py`.

---

## Configuration Reference (`config/guardrails.yaml`)

```yaml
guardrails:
  input:
    mapped_number: 63       # 0b111111 — all 6 input guardrails
    guardrails:
      - name: anti_prompt_injection
        sequence_id: 1
        parameters: { max_suspicious_patterns: 1, redact: false }
      - name: pii_detection
        sequence_id: 2
        parameters: { mode: redact }
      # … toxicity, contextual_relevance, sql_injection, intent_alignment

  output:
    mapped_number: 255      # 0b11111111 — all 8 output guardrails
    guardrails:
      # … json_validator, schema_compliance, logical_consistency,
      #     redundancy_removal, readability, output_quality,
      #     content_filter, brand_safety

llm:
  provider: groq
  model: llama3-8b-8192
  api_key_env: GROQ_API_KEY

pipeline:
  block_on_input_failure: true
  block_on_output_failure: false
  max_concurrent: 4
```

---

## Test Coverage

```
tests/test_bitmask.py           19 tests  — sequence_id validation, is_active, registry filtering
tests/test_input_guardrails.py  17 tests  — injection, PII, toxicity, SQL, intent
tests/test_output_guardrails.py 16 tests  — JSON, redundancy, readability, content, brand, consistency
tests/test_pipeline.py          18 tests  — end-to-end flow, blocking, redaction, bitmask, context

Total: 70 tests  |  All passing
```

Run with:
```bash
pytest tests/ -v
```

---

## Non-Functional Properties

| Property          | Implementation                                                  |
|-------------------|-----------------------------------------------------------------|
| Async             | Full `async/await` throughout; `asyncio.Semaphore` for concurrency |
| Logging           | Structured JSON logs with `correlation_id` on every event       |
| Timeouts          | Per-guardrail `asyncio.wait_for` with configurable seconds      |
| Error handling    | Custom exception hierarchy; fail-safe `SKIP` on error           |
| Type safety       | 100% type-annotated; `from __future__ import annotations`       |
| Extensibility     | Subclass `InputGuardrail` / `OutputGuardrail` + `register()`   |
| Config-driven     | Every threshold, parameter, and activation controlled via YAML  |
| Zero LLM required | All pattern-based guardrails work offline                       |
