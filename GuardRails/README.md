# Guardrails Framework

A production-grade, reusable Python framework for wrapping LLM calls with configurable
**Input Guardrails** (pre-LLM) and **Output Guardrails** (post-LLM).  
Guardrail activation is controlled by a **bitmask** — no code changes needed to
enable, disable, or combine checks.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [How the Bitmask Works](#how-the-bitmask-works)
- [Guardrails Reference](#guardrails-reference)
  - [Input Guardrails](#input-guardrails)
  - [Output Guardrails](#output-guardrails)
- [Pipeline Flow](#pipeline-flow)
- [Configuration](#configuration)
- [Usage Patterns](#usage-patterns)
  - [Programmatic Setup](#1-programmatic-setup)
  - [Config-File Setup](#2-config-file-setup)
  - [Adding a Custom Guardrail](#3-adding-a-custom-guardrail)
  - [Extending the LLM Provider](#4-extending-the-llm-provider)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Key Design Decisions](#key-design-decisions)

---

## Features

- **Bitmask-driven activation** — select any combination of guardrails with a single integer
- **6 Input guardrails** — injection defense, PII detection, toxicity, relevance, SQL injection, intent alignment
- **8 Output guardrails** — JSON validation, schema compliance, consistency, redundancy removal, readability, quality, content filter, brand safety
- **Groq LLM integration** — async HTTP client with retry, back-off, and timeout
- **Provider-agnostic LLM interface** — swap Groq for OpenAI / Azure / Ollama in one class
- **Fully async** — `async/await` throughout; concurrent execution via `asyncio.Semaphore`
- **Structured JSON logging** with correlation IDs on every event
- **Config-driven** — YAML/JSON config controls every threshold, parameter, and activation flag
- **Zero LLM required** — all regex-based guardrails work completely offline
- **Pluggable** — add a new guardrail in under 20 lines by subclassing `InputGuardrail`
- **70 passing tests** — pytest-asyncio with mocked LLM calls

---

## Installation

```bash
# Clone / copy the project
cd guardrails-framework

# Install dependencies
pip install -r requirements.txt
```

**requirements.txt**
```
httpx>=0.27.0
pyyaml>=6.0.1
jsonschema>=4.22.0
pytest>=8.2.0
pytest-asyncio>=0.23.0
```

> `jsonschema` is only needed if you use the **Schema Compliance** output guardrail.  
> `pyyaml` is only needed if you load config from a `.yaml` file.

---

## Quick Start

```python
import asyncio
from guardrails import create_executor

async def main():
    # One-liner setup from config file
    executor = create_executor(
        config_path="config/guardrails.yaml",
        api_key="gsk_...",           # Groq API key; or set GROQ_API_KEY env var
    )

    # Your LLM call (any async function: str → str)
    async def call_llm(prompt: str) -> str:
        return "Paris is the capital of France."

    ctx = await executor.execute_pipeline(
        "What is the capital of France?",
        llm_invoke=call_llm,
    )

    print(ctx.final_output)          # "Paris is the capital of France."
    print(ctx.input_passed)          # True
    print(ctx.output_passed)         # True
    print(ctx.correlation_id)        # UUID for log tracing

asyncio.run(main())
```

---

## How the Bitmask Works

Each guardrail has a unique `sequence_id` that is a **power of 2** (1, 2, 4, 8, 16 …).  
A `mapped_number` integer acts as a bitmask.  
A guardrail executes **only when its bit is set**:

```
guardrail runs  ←→  mapped_number & sequence_id != 0
```

### Example

| Guardrail             | sequence_id | `mapped_number = 19` (binary `010011`) | Active? |
|-----------------------|-------------|----------------------------------------|---------|
| Anti-Prompt Injection | 1           | `19 & 1 = 1`                           | ✅      |
| PII Detection         | 2           | `19 & 2 = 2`                           | ✅      |
| Toxicity              | 4           | `19 & 4 = 0`                           | ❌      |
| Contextual Relevance  | 8           | `19 & 8 = 0`                           | ❌      |
| SQL Injection         | 16          | `19 & 16 = 16`                         | ✅      |
| Intent Alignment      | 32          | `19 & 32 = 0`                          | ❌      |

```python
# Activate all input guardrails
executor = GuardrailExecutor(registry, input_mapped_number=0b111111)   # = 63

# Activate only injection + SQL
executor = GuardrailExecutor(registry, input_mapped_number=0b010001)   # = 17

# Disable all output guardrails
executor = GuardrailExecutor(registry, output_mapped_number=0)
```

---

## Guardrails Reference

### Input Guardrails

| seq_id | Name                       | Technique               | Blocks? | Modifies Input?      |
|--------|----------------------------|-------------------------|---------|----------------------|
| 1      | Anti-Prompt Injection      | 13 compiled regex rules | Yes     | Optional redact mode |
| 2      | PII Detection              | Regex (email, SSN, CC, phone, IP, DOB, passport, IBAN) | Yes | Yes — redact mode |
| 4      | Language Toxicity          | Regex patterns + optional LLM | Yes | No |
| 8      | Contextual Relevance       | Keyword match / LLM     | Yes     | No                   |
| 16     | SQL Injection Prevention   | 16 compiled SQL patterns| Yes     | No                   |
| 32     | Intent Alignment           | LLM (Groq)              | Yes     | No                   |

### Output Guardrails

| seq_id | Name                       | Technique               | Blocks? | Modifies Output? |
|--------|----------------------------|-------------------------|---------|------------------|
| 1      | JSON Validator             | `json.loads`            | Yes     | No               |
| 2      | API Schema Compliance      | `jsonschema`            | Yes     | No               |
| 4      | Logical Consistency        | LLM (Groq)              | Optional| No               |
| 8      | Redundancy Removal         | Jaccard similarity dedup| No      | Yes              |
| 16     | Readability Scoring        | Flesch Reading Ease     | Optional| No               |
| 32     | Output Quality Assessment  | LLM (Groq)              | Optional| No               |
| 64     | Inappropriate Content      | Regex + configurable categories | Yes | No          |
| 128    | Competitor / Brand Safety  | Regex (configurable list)| Optional| No             |

> **LLM-based guardrails** (seq 4, 8, 32 on input; seq 4, 32 on output) return `status=SKIP`
> when no LLM client is configured, so the pipeline continues safely.

---

## Pipeline Flow

```
User Input
    │
    ▼
┌────────────────────────────────────┐
│  Input Guardrails  (sequential)    │  Each may sanitise content for the next.
│  Controlled by input_mapped_number │  Fails raise PipelineBlockedError when
└────────────────────────────────────┘  block_on_input_failure = True.
    │ all pass
    ▼
┌──────────────────┐
│  LLM Invocation  │  Receives the (possibly sanitised) prompt.
└──────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Output Guardrails  (sequential)    │  Each may refine the output.
│  Controlled by output_mapped_number │
└─────────────────────────────────────┘
    │
    ▼
PipelineContext.final_output
```

### `PipelineContext` — what you get back

| Field             | Type           | Description                                         |
|-------------------|----------------|-----------------------------------------------------|
| `correlation_id`  | `str` (UUID)   | Unique ID for log tracing across all guardrails     |
| `original_input`  | `str`          | The raw user prompt                                 |
| `sanitized_input` | `str \| None`  | Modified input (e.g. PII redacted)                  |
| `llm_response`    | `str \| None`  | Raw LLM output                                      |
| `final_output`    | `str \| None`  | Output after all output guardrails                  |
| `input_results`   | `list`         | `GuardrailResult` for every input guardrail that ran |
| `output_results`  | `list`         | `GuardrailResult` for every output guardrail that ran|
| `input_passed`    | `bool`         | True if all input guardrails passed or were skipped  |
| `output_passed`   | `bool`         | True if all output guardrails passed or were skipped |
| `metadata`        | `dict`         | Arbitrary data written by guardrails (readability scores, detected intent, etc.) |

---

## Configuration

The full default config lives in [config/guardrails.yaml](config/guardrails.yaml).

```yaml
guardrails:
  input:
    mapped_number: 63           # all 6 input guardrails (1+2+4+8+16+32)
    guardrails:
      - name: anti_prompt_injection
        sequence_id: 1
        enabled: true
        threshold: 0.5
        timeout_seconds: 5.0
        parameters:
          max_suspicious_patterns: 1
          redact: false

      - name: pii_detection
        sequence_id: 2
        parameters:
          mode: redact           # "redact" sanitises; "fail" blocks
          enabled_types: [EMAIL, US_PHONE, US_SSN, CREDIT_CARD, IP_ADDRESS, DOB]

      # … toxicity, contextual_relevance, sql_injection, intent_alignment

  output:
    mapped_number: 255          # all 8 output guardrails
    guardrails:
      - name: json_validator
        sequence_id: 1
        parameters:
          required: false        # only validate if output looks like JSON

      - name: brand_safety
        sequence_id: 128
        parameters:
          competitors: ["CompetitorA", "CompetitorB"]
          brand_name: "MyBrand"
          block_on_competitor_mention: false

      # … schema_compliance, logical_consistency, redundancy_removal,
      #     readability, output_quality, content_filter

llm:
  provider: groq
  model: llama3-8b-8192
  api_key_env: GROQ_API_KEY     # env var to read the key from

pipeline:
  block_on_input_failure: true
  block_on_output_failure: false
  max_concurrent: 4

logging:
  level: INFO
  structured: true              # JSON lines to stdout
  log_file: null                # optional file path
```

---

## Usage Patterns

### 1. Programmatic Setup

Ideal for microservices or when you want full control in code.

```python
import asyncio
from guardrails.executor.executor import GuardrailExecutor
from guardrails.input.prompt_injection import AntiPromptInjectionGuardrail
from guardrails.input.pii_detection import PIIDetectionGuardrail
from guardrails.output.redundancy import RedundancyRemovalGuardrail
from guardrails.models.types import GuardrailConfig
from guardrails.registry.registry import GuardrailRegistry
from guardrails.utils.exceptions import PipelineBlockedError

registry = GuardrailRegistry()
registry.register(AntiPromptInjectionGuardrail(
    GuardrailConfig(name="injection", sequence_id=1)
))
registry.register(PIIDetectionGuardrail(
    GuardrailConfig(name="pii", sequence_id=2, parameters={"mode": "redact"})
))
registry.register(RedundancyRemovalGuardrail(
    GuardrailConfig(name="redundancy", sequence_id=8)
))

executor = GuardrailExecutor(
    registry=registry,
    input_mapped_number=3,      # bits 1+2 → injection + pii
    output_mapped_number=8,     # bit 8   → redundancy removal
    block_on_input_failure=True,
)

async def main():
    try:
        ctx = await executor.execute_pipeline(
            "My SSN is 123-45-6789. Summarise quantum computing.",
            llm_invoke=lambda p: asyncio.sleep(0, "Quantum computing uses qubits."),
        )
        print("Sanitised input:", ctx.sanitized_input)
        print("Output:", ctx.final_output)
    except PipelineBlockedError as e:
        print("Blocked:", e)

asyncio.run(main())
```

### 2. Config-File Setup

```python
from guardrails import create_executor
import asyncio, os

executor = create_executor(
    config_path="config/guardrails.yaml",
    api_key=os.getenv("GROQ_API_KEY"),
)

async def my_llm(prompt: str) -> str:
    # replace with real Groq / OpenAI call
    return "This is the LLM response."

ctx = asyncio.run(executor.execute_pipeline("Tell me about Python.", llm_invoke=my_llm))
print(ctx.final_output)
```

### 3. Adding a Custom Guardrail

Subclass `InputGuardrail` or `OutputGuardrail` and implement `_execute`.  
The framework handles timing, logging, timeouts, and error capture automatically.

```python
from guardrails.base.guardrail import InputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

class WordLimitGuardrail(InputGuardrail):
    """Reject inputs that exceed a configurable word count."""

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        max_words: int = self.config.parameters.get("max_words", 100)
        count = len(content.split())
        if count > max_words:
            return self._fail_result(
                score=max_words / count,
                message=f"Input too long: {count} words (max {max_words})",
                flags=["TOO_LONG"],
            )
        return self._pass_result(score=1.0, message=f"{count} words — OK")

# Register with any unused power-of-2 sequence_id
registry.register(
    WordLimitGuardrail(GuardrailConfig("word_limit", sequence_id=64, parameters={"max_words": 50}))
)
```

### 4. Extending the LLM Provider

```python
from guardrails.llm.client import LLMClient, LLMMessage, LLMResponse
from typing import List

class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        import openai
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = model

    async def complete(
        self, messages: List[LLMMessage], *, temperature=0.0, max_tokens=512, timeout=10.0
    ) -> LLMResponse:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return LLMResponse(content=resp.choices[0].message.content, model=self._model)

    async def health_check(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False

# Pass to any LLM-dependent guardrail
from guardrails.input.intent_alignment import IntentAlignmentGuardrail
from guardrails.models.types import GuardrailConfig

llm = OpenAIClient(api_key="sk-...")
registry.register(IntentAlignmentGuardrail(
    GuardrailConfig("intent", sequence_id=32), llm_client=llm
))
```

---

## Project Structure

```
guardrails-framework/
├── guardrails/
│   ├── __init__.py                 # Public API: create_executor, GuardrailExecutor, …
│   ├── factory.py                  # create_executor() — wires everything from config
│   ├── models/types.py             # GuardrailResult, PipelineContext, GuardrailConfig, enums
│   ├── base/guardrail.py           # BaseGuardrail (abstract), InputGuardrail, OutputGuardrail
│   ├── llm/
│   │   ├── client.py               # LLMClient (abstract), LLMMessage, LLMResponse, parse_llm_json
│   │   └── groq_client.py          # GroqLLMClient — httpx async, retry, back-off
│   ├── registry/registry.py        # GuardrailRegistry — register, discover, bitmask-filter
│   ├── executor/executor.py        # GuardrailExecutor — full pipeline orchestration
│   ├── input/
│   │   ├── prompt_injection.py     # seq 1  — Anti-Prompt Injection
│   │   ├── pii_detection.py        # seq 2  — PII Detection & Redaction
│   │   ├── toxicity.py             # seq 4  — Language Toxicity
│   │   ├── relevance.py            # seq 8  — Contextual Relevance
│   │   ├── sql_injection.py        # seq 16 — SQL Injection Prevention
│   │   └── intent_alignment.py     # seq 32 — Intent Alignment (LLM)
│   ├── output/
│   │   ├── json_validator.py       # seq 1   — JSON Validator
│   │   ├── schema_compliance.py    # seq 2   — API Schema Compliance
│   │   ├── consistency.py          # seq 4   — Logical Consistency (LLM)
│   │   ├── redundancy.py           # seq 8   — Redundancy Removal
│   │   ├── readability.py          # seq 16  — Flesch Readability Scoring
│   │   ├── quality.py              # seq 32  — Output Quality Assessment (LLM)
│   │   ├── content_filter.py       # seq 64  — Inappropriate Content Filter
│   │   └── brand_safety.py         # seq 128 — Competitor Shield & Brand Safety
│   ├── config/loader.py            # YAML/JSON → FrameworkConfig dataclasses
│   └── utils/
│       ├── exceptions.py           # PipelineBlockedError, LLMClientError, RegistryError …
│       └── log_config.py           # Structured JSON logging with correlation IDs
│
├── config/
│   └── guardrails.yaml             # Reference configuration
│
├── tests/
│   ├── conftest.py                 # Fixtures: mock LLM, contexts, config helpers
│   ├── test_bitmask.py             # Bitmask activation & registry logic
│   ├── test_input_guardrails.py    # Per-guardrail unit tests
│   ├── test_output_guardrails.py   # Per-guardrail unit tests
│   └── test_pipeline.py            # End-to-end pipeline integration tests
│
├── examples/
│   └── example_usage.py            # Programmatic, config-file, and custom guardrail demos
│
├── summary.md
├── README.md
├── requirements.txt
└── pytest.ini
```

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# A specific module
pytest tests/test_bitmask.py -v
pytest tests/test_pipeline.py -v

# With coverage (requires pytest-cov)
pytest tests/ --cov=guardrails --cov-report=term-missing
```

Expected output:

```
70 passed in 0.12s
```

All LLM calls are mocked with `unittest.mock.AsyncMock` — no API key required to run tests.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Bitmask activation | O(1) check; config stored as a single integer; easy to audit via `bin(mapped_number)` |
| Sequential input guardrails | Each guardrail may sanitise content that the next guardrail sees (e.g. PII redaction before injection check) |
| SKIP on LLM-absent | LLM-based checks degrade gracefully — the pipeline never breaks just because no API key is set |
| `modified_content` field | Guardrails signal content changes without mutating shared state; the executor applies them in order |
| Custom exception hierarchy | `PipelineBlockedError` carries the list of failing guardrails so callers can respond with context |
| `correlation_id` on context | Every log line carries the same UUID, making distributed traces trivial to filter |
| No global state | Registry, executor, and all guardrails are plain objects — safe to instantiate multiple times for multi-tenant use |

---

## License

MIT
