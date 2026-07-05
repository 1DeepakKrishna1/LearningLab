# Agentic AI Design Patterns

A production-quality Python reference implementation of **21 agentic AI design patterns** using the [Groq](https://groq.com/) API (`llama-3.3-70b-versatile`). Every pattern shares a unified `GroqClient` interface and follows consistent conventions: type hints, async I/O, structured dataclasses, and layered error handling.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Unified Architecture](#unified-architecture)
- [Pattern Reference](#pattern-reference)
  - [Group 1 — Core Patterns (1–7)](#group-1--core-patterns-17)
  - [Group 2 — Extended Patterns (8–14)](#group-2--extended-patterns-814)
  - [Group 3 — Advanced Patterns (15–21)](#group-3--advanced-patterns-1521)
- [CLI Usage](#cli-usage)
- [Dependencies](#dependencies)

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your Groq API key
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key_here
# OR: export GROQ_API_KEY=your_key_here

# 3. List all 21 patterns
python main.py --list

# 4. Run a single pattern
python main.py --pattern 5

# 5. Run a group of patterns
python main.py --from 15 --to 21

# 6. Run all patterns
python main.py
```

---

## Project Structure

```
AgenticPatterns/
├── llm_client.py              # Unified async Groq client (shared by all patterns)
├── main.py                    # CLI demo runner — run any/all patterns
├── requirements.txt
├── .env.example
└── patterns/
    ├── base.py                     # BasePattern abstract class
    │
    ├── # Group 1 — Core (1–7)
    ├── prompt_chaining.py
    ├── routing.py
    ├── parallelization.py
    ├── reflection.py
    ├── tool_use.py
    ├── planning.py
    ├── multi_agent.py
    │
    ├── # Group 2 — Extended (8–14)
    ├── memory_management.py
    ├── learning_adaptation.py
    ├── model_context_protocol.py
    ├── goal_monitoring.py
    ├── exception_recovery.py
    ├── human_in_the_loop.py
    ├── knowledge_retrieval.py
    │
    └── # Group 3 — Advanced (15–21)
        ├── inter_agent_communication.py
        ├── resource_optimization.py
        ├── reasoning_techniques.py
        ├── guardrails_safety.py
        ├── evaluation_monitoring.py
        ├── prioritization.py
        └── exploration_discovery.py
```

---

## Unified Architecture

All patterns share the same foundation:

```python
# Every pattern inherits from BasePattern
class MyPattern(BasePattern):
    name = "N · Pattern Name"

    async def run(self, **kwargs) -> Any:
        ...

# All patterns receive a shared GroqClient
client = GroqClient()          # reads GROQ_API_KEY from env
pattern = MyPattern(client)
result = await pattern.run(topic="...")
```

**`GroqClient`** exposes two methods:

| Method | Use |
|--------|-----|
| `complete(messages, *, tools, model, ...)` | Full control — returns `LLMResponse` with token counts and tool calls |
| `complete_text(prompt, *, system, ...)` | Convenience wrapper — returns plain text |

---

## Pattern Reference

---

### Group 1 — Core Patterns (1–7)

---

#### Pattern 1 · Prompt Chaining

**File:** `patterns/prompt_chaining.py`

**What it is:** A sequential pipeline where the output of each LLM call becomes the input for the next. Each step transforms or refines the content.

**How it works:**
```
Topic → [Step 1] Outline → [Step 2] Draft → [Step 3] Edit → [Step 4] Headline
```

**Key components:**
- `ChainResult` dataclass holds all intermediate outputs
- Each step uses a specialised system prompt tailored to its role
- Steps are deliberately sequential — each depends on the previous

**Real-world use cases:**
| Use Case | Chain Steps |
|----------|-------------|
| Content creation pipeline | Brief → Outline → Draft → SEO metadata |
| Code review automation | Code → Static analysis → Explanation → Ticket |
| Document translation | Source → Literal translation → Naturalisation → Review |
| Research summarisation | Raw data → Key findings → Executive summary → Tweet |
| Email drafting | Intent → Tone-adjusted draft → Grammar check → Subject line |

---

#### Pattern 2 · Routing

**File:** `patterns/routing.py`

**What it is:** A lightweight classifier LLM call categorises the user's query, then routes it to a specialist handler with the most appropriate system prompt.

**How it works:**
```
Query → [Classifier: FAST_MODEL, temp=0.0] → category
      → [Specialist system prompt] → Response
```

**Route map:**
| Category | System Prompt Persona |
|----------|-----------------------|
| `technical` | Senior software engineer with code examples |
| `creative` | Creative writer with narrative response |
| `analytical` | Strategic analyst with structured sections |
| `general` | Friendly, conversational assistant |

**Real-world use cases:**
| Use Case | Routes |
|----------|--------|
| Customer support bot | billing / technical / returns / general |
| Developer assistant | code / docs / architecture / debugging |
| Medical triage system | urgent / appointment / medication / general |
| Legal query router | contracts / litigation / compliance / general |
| Multi-lingual support | language detection → locale-specific handler |

---

#### Pattern 3 · Parallelization

**File:** `patterns/parallelization.py`

**What it is:** Multiple independent LLM calls execute concurrently via `asyncio.gather()`. A fan-in synthesis step aggregates all results.

**How it works:**
```
Topic ──┬─→ [Optimist analysis]  ─┐
        ├─→ [Pessimist analysis] ─┼─→ [Synthesis] → Balanced report
        └─→ [Realist analysis]   ─┘
        (all 3 run in parallel)
```

**Real-world use cases:**
| Use Case | Parallel Branches |
|----------|-------------------|
| Market research | Competitor A / B / C analysis simultaneously |
| Code generation | Frontend + backend + tests generated in parallel |
| Risk assessment | Technical / financial / legal / operational risks |
| News aggregation | Summarise 5 articles about the same event in parallel |
| A/B content generation | 3 headline variants generated and scored concurrently |

---

#### Pattern 4 · Reflection

**File:** `patterns/reflection.py`

**What it is:** The LLM generates an initial output, then acts as its own critic, then rewrites to address the critique. This loop can run for N iterations.

**How it works:**
```
Task → [Generate] → Initial output
     → [Critique] → Numbered issues
     → [Improve]  → Revised output
     (repeat N times)
```

**Key components:**
- `ReflectionIteration` stores each cycle's code + critique
- Configurable `iterations` parameter
- Separate system prompts for Generator, Critic, and Improver roles

**Real-world use cases:**
| Use Case | What Gets Reflected |
|----------|---------------------|
| Code generation | Correctness, edge cases, readability, efficiency |
| Essay writing | Argument strength, evidence, clarity, structure |
| API design | Naming, consistency, versioning, error handling |
| SQL query optimisation | Performance, index usage, readability |
| Test case writing | Coverage, edge cases, assertion quality |

---

#### Pattern 5 · Tool Use

**File:** `patterns/tool_use.py`

**What it is:** The LLM is given a set of callable functions. It autonomously decides which tools to invoke, executes them locally, and feeds results back into the conversation until it produces a final answer.

**How it works:**
```
User query → LLM → tool_call(calculator, "sqrt(1764)")
           → Execute tool locally → "42"
           → LLM → tool_call(unit_converter, ...) → "26.1 miles"
           → LLM → Final answer (no more tool calls)
```

**Built-in tools:**
| Tool | Description |
|------|-------------|
| `calculator` | Evaluate safe math expressions (sqrt, log, trig, etc.) |
| `get_current_date` | Return today's ISO date |
| `count_words` | Count words in a text |
| `unit_converter` | Convert km↔miles, kg↔lbs, °C↔°F, m↔ft |

**Real-world use cases:**
| Use Case | Tools |
|----------|-------|
| Data analyst assistant | SQL executor, chart renderer, stats calculator |
| DevOps agent | Shell commands, log parser, metric queries |
| Financial advisor bot | Stock API, currency converter, compound interest calculator |
| Travel planning agent | Flight search, hotel API, currency conversion, weather |
| Research assistant | Web search, PDF reader, citation formatter |

---

#### Pattern 6 · Planning

**File:** `patterns/planning.py`

**What it is:** The LLM first decomposes a complex goal into an ordered plan (JSON list of steps), then executes each step sequentially, maintaining an accumulating context so later steps can reference earlier outputs.

**How it works:**
```
Goal → [Phase 1: Plan]    → ["Step 1", "Step 2", ..., "Step N"] (JSON)
     → [Phase 2: Execute] → Step 1 output
                          → Step 2 output (sees Step 1 context)
                          → Step N output (sees all prior context)
     → [Phase 3: Consolidate] → Final document
```

**Real-world use cases:**
| Use Case | Plan Steps |
|----------|------------|
| Go-to-market strategy | Market analysis → ICP → Positioning → Channels → Metrics |
| Software architecture | Requirements → Components → Data model → APIs → Security |
| Research paper outline | Problem → Literature → Methodology → Results → Conclusions |
| Incident response | Detect → Contain → Investigate → Remediate → Post-mortem |
| Feature specification | User story → Acceptance criteria → Technical design → Test plan |

---

#### Pattern 7 · Multi-Agent

**File:** `patterns/multi_agent.py`

**What it is:** Multiple specialised agents, each with a distinct role and system prompt, collaborate on a shared task. An Orchestrator coordinates the workflow.

**How it works:**
```
Orchestrator → defines instructions for each agent
             → ResearchAgent  → gathers facts (history=[])
             → WriterAgent    → drafts article (history=[research])
             → ReviewerAgent  → reviews & polishes (history=[research, draft])
```

**Agent roles:**
| Agent | Role |
|-------|------|
| `Orchestrator` | Plans the workflow, provides instructions to each specialist |
| `ResearchAgent` | Gathers facts, trends, statistics |
| `WriterAgent` | Drafts content from the research brief |
| `ReviewerAgent` | Critiques and produces the final polished version |

**Real-world use cases:**
| Use Case | Agent Roster |
|----------|-------------|
| Automated journalism | Researcher + Writer + Editor + Fact-checker |
| Software development | Architect + Developer + Code Reviewer + Tech Writer |
| Marketing campaign | Strategist + Copywriter + Designer brief + Analytics |
| Legal document review | Paralegal + Senior attorney + Compliance checker |
| Data pipeline | Data Engineer + Analyst + QA + Report Writer |

---

### Group 2 — Extended Patterns (8–14)

---

#### Pattern 8 · Memory Management

**File:** `patterns/memory_management.py`

**What it is:** Agents maintain persistent state across turns using two complementary memory layers — a bounded short-term conversation buffer and a persistent long-term key-value fact store.

**Memory architecture:**
```
┌──────────────────────────────────────────────────┐
│  Short-Term Memory (STM)                         │
│  Sliding window of last N message pairs          │
│  Provides recent conversation context            │
├──────────────────────────────────────────────────┤
│  Long-Term Memory (LTM)                          │
│  Persistent key-value facts extracted from turns │
│  Injected into system prompt on every call       │
└──────────────────────────────────────────────────┘
```

**Fact extraction:** The agent embeds `\`\`\`memory {"key": ..., "value": ...}\`\`\`` blocks in its replies; the pipeline parses and stores them in LTM automatically.

**Real-world use cases:**
| Use Case | What to Remember |
|----------|-----------------|
| Personal assistant | Name, preferences, schedule, relationships |
| Customer support | Previous tickets, product tier, communication style |
| Tutoring agent | Learning progress, weak areas, preferred explanation style |
| Health coach | Medical history, goals, dietary restrictions, activity level |
| Sales agent | Company info, deal stage, objections raised, contact preferences |

---

#### Pattern 9 · Learning and Adaptation

**File:** `patterns/learning_adaptation.py`

**What it is:** The agent collects explicit user feedback (rating + comment), updates a `PreferenceProfile` using LLM-parsed preference extraction, and injects the learned profile into its system prompt on subsequent requests.

**Adaptation loop:**
```
Response₁ → User feedback (rating=2, "too verbose")
          → [LLM updates PreferenceProfile: length=concise, format=bullets]
          → Response₂ (shorter, bullet-point format)
          → User feedback (rating=4, "add complexity info")
          → [LLM updates PreferenceProfile: style_notes+="include Big-O"]
          → Response₃ (final, fully adapted)
```

**Real-world use cases:**
| Use Case | What Adapts |
|----------|-------------|
| Code assistant | Verbosity, language preference, comment density |
| Writing tool | Tone (formal/casual), length, structure (prose vs bullets) |
| Teaching agent | Explanation depth, analogy style, prior knowledge level |
| Email drafter | Formality, length, sign-off style per recipient |
| Report generator | Section structure, chart preferences, audience vocabulary |

---

#### Pattern 10 · Model Context Protocol (MCP)

**File:** `patterns/model_context_protocol.py`

**What it is:** A simulation of Anthropic's Model Context Protocol — a JSON-RPC 2.0-style standard for AI models to discover and interact with external tools, data resources, and prompt templates.

**MCP concepts implemented:**
| Concept | Description |
|---------|-------------|
| `AgentCard` | Server identity and capability declaration |
| `tools/list` | Discover available tools |
| `tools/call` | Invoke a tool by name with typed arguments |
| `resources/list` | Discover available data sources |
| `resources/read` | Read a resource by URI |
| `prompts/list` | Discover reusable prompt templates |
| `prompts/get` | Retrieve a filled prompt template |

**Real-world use cases:**
| Use Case | MCP Resources |
|----------|---------------|
| Enterprise AI assistant | CRM data, internal docs, calendar, Jira tickets |
| Code assistant | Git repo, CI/CD status, test results, documentation |
| Data analyst | Database schemas, CSV files, chart templates |
| DevOps agent | Server metrics, deployment manifests, runbooks |
| Research agent | Academic databases, citation tools, knowledge graphs |

---

#### Pattern 11 · Goal Setting and Monitoring

**File:** `patterns/goal_monitoring.py`

**What it is:** The agent operates around an explicit SMART goal hierarchy. It decomposes objectives into milestones, executes work for each, assesses completion with an LLM judge, and generates structured progress reports.

**Goal lifecycle:**
```
Goal → [Phase 1: Decompose] → Milestone 1, 2, 3, 4 (JSON)
     → [Phase 2: Execute]   → Artefact per milestone
     → [Phase 3: Assess]    → Completion % + status per milestone
     → [Phase 4: Monitor]   → Dashboard + progress report
```

**Milestone statuses:** `pending` → `in_progress` → `complete` / `blocked`

**Real-world use cases:**
| Use Case | Milestones |
|----------|-----------|
| Product launch | Research → MVP → Beta → Marketing → Launch |
| OKR tracking | Define KRs → Weekly check-ins → Mid-quarter review → Final |
| Project management | Planning → Design → Build → Test → Deploy |
| Learning curriculum | Foundations → Core concepts → Projects → Assessment |
| Startup fundraising | Pitch deck → Financial model → Investor outreach → Term sheet |

---

#### Pattern 12 · Exception Handling and Recovery

**File:** `patterns/exception_recovery.py`

**What it is:** A 4-layer recovery chain handles failures gracefully. Each layer is tried in sequence until one succeeds or all fail, with graceful degradation as the final fallback.

**Recovery layers:**
```
Layer 1: Retry with exponential back-off  (transient errors: rate limits, timeouts)
       ↓ (if exhausted)
Layer 2: Prompt simplification            (strip complex prompt to core question)
       ↓ (if failed)
Layer 3: Model fallback                   (switch to FAST_MODEL)
       ↓ (if failed)
Layer 4: Graceful degradation             (return structured error report)
```

**Error classification:** `LLMRateLimitError` | `LLMTimeoutError` | `LLMError` | `Unknown`

**Real-world use cases:**
| Use Case | Recovery Strategy |
|----------|------------------|
| Production API gateway | Retry → fallback model → cached response |
| Batch processing pipeline | Retry → simplify → partial result → skip with log |
| Real-time chatbot | Retry → fast model → canned response |
| Financial transaction agent | Retry → human escalation → reject with reason |
| Medical information system | Retry → simplified query → "please consult a doctor" |

---

#### Pattern 13 · Human-in-the-Loop (HITL)

**File:** `patterns/human_in_the_loop.py`

**What it is:** Critical decision points pause the pipeline and present the agent's proposed action to a human for review. Three checkpoint types provide granular control over what requires human oversight.

**Checkpoint types:**
| Type | Behaviour |
|------|-----------|
| `APPROVE_REJECT` | Binary gate — rejection cancels the workflow |
| `APPROVE_MODIFY` | Human can approve as-is or provide edited content |
| `INFORM` | Non-blocking notification — always continues |

**Real-world use cases:**
| Use Case | Checkpoint Placement |
|----------|---------------------|
| Content publishing | Outline review → Draft approval → Social posts (inform) |
| Code deployment | PR review → Staging approval → Production gate |
| Financial transactions | Trade proposal → Risk review → Execution approval |
| Medical recommendations | Diagnosis draft → Physician review → Patient communication |
| Legal document generation | Draft → Lawyer review → Client signature gate |

---

#### Pattern 14 · Knowledge Retrieval (RAG)

**File:** `patterns/knowledge_retrieval.py`

**What it is:** Retrieval-Augmented Generation grounds LLM responses in an authoritative document corpus. Documents are chunked, indexed with BM25, and the most relevant chunks are injected into the prompt.

**RAG pipeline:**
```
Documents → [Chunker] → Chunks → [BM25 Index]
Query → [BM25 Retriever] → Top-K chunks
      → [Augment prompt] → LLM → Cited answer
```

**BM25 retriever:** Pure Python implementation (no external vector DB required). Uses IDF weighting, term frequency saturation (k1=1.5), and document length normalisation (b=0.75).

**Real-world use cases:**
| Use Case | Knowledge Base |
|----------|---------------|
| Enterprise Q&A bot | Internal policies, procedures, HR docs |
| Developer documentation | API references, tutorials, changelog |
| Legal research assistant | Case law, statutes, contracts |
| Medical reference system | Clinical guidelines, drug interactions, research papers |
| Customer support | Product manuals, FAQs, troubleshooting guides |

---

### Group 3 — Advanced Patterns (15–21)

---

#### Pattern 15 · Inter-Agent Communication (A2A)

**File:** `patterns/inter_agent_communication.py`

**What it is:** Agents communicate via a structured message protocol (modelled on Google's Agent-to-Agent protocol). Each agent has a typed mailbox; messages are routed through a central registry.

**A2A Protocol:**
```
┌─────────────────────────────────────────────────┐
│  AgentRegistry  (central routing & discovery)   │
└────────┬──────────────────────────┬─────────────┘
         │ route(A2AMessage)        │
    ┌────▼────┐              ┌──────▼──────┐
    │ Mailbox │              │   Mailbox   │
    │ Agent A │              │   Agent B   │
    └─────────┘              └─────────────┘
```

**Message types:** `REQUEST` | `RESPONSE` | `BROADCAST` | `HANDOFF` | `ACK`

**Demo pipeline:** Orchestrator → ResearchAgent → WriterAgent ⇄ EditorAgent → Orchestrator

**Real-world use cases:**
| Use Case | Agent Network |
|----------|--------------|
| Distributed CI/CD | Linter + Test runner + Security scanner + Deploy agent |
| Supply chain optimisation | Procurement + Inventory + Logistics + Finance agents |
| Incident response | Alert triage + Root cause + Remediation + Notification agents |
| Content moderation | OCR + Language detector + Policy checker + Actioner agents |
| Trading system | Data feed + Signal generator + Risk manager + Order executor |

---

#### Pattern 16 · Resource-Aware Optimization

**File:** `patterns/resource_optimization.py`

**What it is:** The agent monitors its own resource consumption (tokens, API calls, time, cost) and dynamically downgrades its strategy as budgets deplete, maximising output quality within constraints.

**Adaptive strategy tiers:**
| Budget remaining | Strategy |
|-----------------|----------|
| > 60% | Default model, full `max_tokens` |
| 30–60% | Default model, reduced `max_tokens` |
| 10–30% | Switch to `FAST_MODEL` |
| < 10% | Minimal tokens, skip non-essential steps |

**Real-world use cases:**
| Use Case | Budget Constraint |
|----------|------------------|
| Serverless AI function | Token cost ceiling per invocation |
| Batch nightly processing | Total daily API spend limit |
| Real-time assistant | Latency SLA (must respond within 2 seconds) |
| Free-tier app | Monthly token quota management |
| Multi-tenant SaaS | Per-user token allocation enforcement |

---

#### Pattern 17 · Reasoning Techniques

**File:** `patterns/reasoning_techniques.py`

**What it is:** Four advanced reasoning strategies applied to the same problem, with results compared side-by-side.

**Techniques:**

| Technique | Mechanism | Best for |
|-----------|-----------|----------|
| **Chain-of-Thought (CoT)** | Explicit numbered steps before answering | Maths, logic, structured analysis |
| **Tree-of-Thought (ToT)** | N branches generated in parallel, LLM evaluates and selects best | Creative problems, optimisation |
| **ReAct** | Thought → Action → Observation loop with tool calls | Tool-augmented reasoning, multi-step tasks |
| **Self-Consistency (SC)** | N independent samples at high temperature, majority vote | Factual queries, ambiguous problems |

**Real-world use cases:**
| Use Case | Recommended Technique |
|----------|-----------------------|
| Complex mathematical proofs | CoT or SC (verify answer) |
| Strategic planning | ToT (explore multiple strategies) |
| Code debugging with tools | ReAct (run tests, observe output) |
| Medical diagnosis support | SC (multiple reasoning paths, consensus) |
| Financial modelling | CoT + SC (show working, verify) |

---

#### Pattern 18 · Guardrails and Safety

**File:** `patterns/guardrails_safety.py`

**What it is:** Multi-layer safety enforcement at every boundary — input validation before the LLM sees the prompt, and output validation before the response reaches the user.

**Guardrail stack:**
```
User Input
    ↓ [Input Guardrails]
    ├── Prompt injection detection  (regex heuristics)
    ├── PII detection & redaction   (email, phone, SSN, CC, IP)
    ├── Topic policy enforcement    (blocked subject areas)
    └── Input length validation
    ↓ (if all pass)
    LLM Call
    ↓ [Output Guardrails]
    ├── LLM harm screener           (0–10 safety score via judge model)
    ├── PII leakage detection       (ensure no PII in response)
    ├── Output length validation    (min/max word count)
    └── Disclaimer injection        (medical / legal / financial)
    ↓
User Response
```

**Real-world use cases:**
| Use Case | Key Guardrails |
|----------|---------------|
| Public-facing chatbot | Injection detection, topic policy, harm screening |
| Healthcare information | PII redaction, medical disclaimers, harm screening |
| Children's education | Content policy, topic restrictions, age-appropriate filter |
| Financial advice tool | PII protection, financial disclaimers, regulatory compliance |
| Enterprise internal tool | Data loss prevention (PII), topic scope enforcement |

---

#### Pattern 19 · Evaluation and Monitoring

**File:** `patterns/evaluation_monitoring.py`

**What it is:** Automated quality measurement for AI agent outputs using LLM-as-judge scoring, A/B configuration comparison, and statistical drift monitoring.

**Evaluation components:**

| Component | Description |
|-----------|-------------|
| `LLMJudge` | Scores responses on 5 dimensions (relevance, accuracy, completeness, clarity, conciseness) using a separate judge LLM call (G-Eval style) |
| `ABComparator` | Evaluates two responses to the same prompt in parallel; determines winner by overall score |
| `EvalSuite` | Runs a battery of test cases and aggregates metrics with `statistics.mean` |
| `DriftMonitor` | Tracks metric history across runs; fires `DriftAlert` when a dimension degrades beyond threshold |

**Real-world use cases:**
| Use Case | Evaluation Goal |
|----------|----------------|
| Model upgrade testing | Confirm new model ≥ old model across all dimensions |
| Prompt regression testing | Catch quality regressions before deployment |
| A/B prompt experiments | Choose the better system prompt for production |
| Continuous quality monitoring | Alert when production responses degrade |
| Fine-tuning evaluation | Measure improvement across task-specific dimensions |

---

#### Pattern 20 · Prioritization

**File:** `patterns/prioritization.py`

**What it is:** A multi-framework task scheduler that scores backlog items using the Eisenhower Matrix and RICE methodology, then executes them in priority order using a dependency-aware heap queue.

**Scoring frameworks:**

**Eisenhower Matrix** (Urgency × Importance):
| | Important | Not Important |
|-|-----------|---------------|
| **Urgent** | Q1: Do Now | Q3: Delegate |
| **Not Urgent** | Q2: Schedule | Q4: Eliminate |

**RICE Score** = (Reach × Impact × Confidence%) / Effort

**Composite score** = Eisenhower weight × 15 + RICE × 10 + Priority override × 0.5

**Real-world use cases:**
| Use Case | Prioritisation Criteria |
|----------|------------------------|
| Product backlog management | User impact (RICE) + business urgency (Eisenhower) |
| Incident queue triage | Severity + affected users + time-to-fix |
| Sales pipeline management | Deal size + close probability + effort |
| IT helpdesk | SLA tier + business impact + resource availability |
| Research project selection | Scientific value + feasibility + strategic fit |

---

#### Pattern 21 · Exploration and Discovery

**File:** `patterns/exploration_discovery.py`

**What it is:** An autonomous agent starts from a seed concept and self-directs its own research, progressively building a knowledge graph by generating questions, answering them, extracting new concepts, and exploring outward.

**Exploration loop:**
```
Seed concept
    ↓ [Generate questions]  — "What are the key properties of X?"
    ↓ [Answer questions]    — LLM answers each question
    ↓ [Extract concepts]    — find new concepts mentioned in answers
    ↓ [Score novelty]       — deprioritise already-known concepts
    ↓ [Add to frontier]     — queue new concepts for exploration
    ↓ (repeat until max_nodes or convergence)
    → Knowledge graph with N concepts and M relationships
```

**Exploration strategies:**
| Strategy | Behaviour | Best for |
|----------|-----------|----------|
| `BFS` | Broad coverage level by level | Domain mapping, overview |
| `DFS` | Deep dive down one thread | Specialised research |
| `BEST_FIRST` | Follow highest-novelty concepts first | Discovering unknown unknowns |

**Real-world use cases:**
| Use Case | Seed Concept |
|----------|-------------|
| Competitive intelligence | Company name → products, customers, partners |
| Technology scouting | "Quantum cryptography" → related techs, use cases |
| Academic literature mapping | Research topic → key papers, authors, subfields |
| Market research | Product category → trends, players, regulations |
| Threat intelligence | CVE entry → attack vectors, mitigations, related CVEs |

---

## CLI Usage

```bash
# List all 21 patterns (grouped by tier)
python main.py --list

# Run one pattern by number
python main.py --pattern 1      # Prompt Chaining
python main.py --pattern 17     # Reasoning Techniques
python main.py --pattern 21     # Exploration and Discovery

# Run a range of patterns
python main.py --from 1  --to 7    # Core patterns only
python main.py --from 8  --to 14   # Extended patterns only
python main.py --from 15 --to 21   # Advanced patterns only

# Run all 21 patterns sequentially
python main.py

# Enable debug logging
python main.py --pattern 5 --verbose
```

---

## Dependencies

```
groq>=0.11.0          # Groq async client (llama-3.3-70b-versatile, llama-3.1-8b-instant)
python-dotenv>=1.0.0  # GROQ_API_KEY loaded from .env
```

All other components (BM25 retrieval, priority queue, knowledge graph, MCP server, guardrail patterns) are implemented in **pure Python** with no additional dependencies.

---

## Models Used

| Model | Used for |
|-------|----------|
| `llama-3.3-70b-versatile` | Default — all primary generation tasks |
| `llama-3.1-8b-instant` | Fast path — classifiers, judges, triage, resource-constrained calls |

Both models are served through Groq's inference API and configured via `GroqClient(model=...)` or per-call overrides.
