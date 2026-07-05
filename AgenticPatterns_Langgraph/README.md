# Agentic AI Design Patterns — LangGraph + Groq

Production-quality Python implementations of **21 Agentic AI design patterns** using [LangGraph](https://github.com/langchain-ai/langgraph) for orchestration and [Groq](https://console.groq.com) as the ultra-fast LLM provider.

---

## Quick Start

```bash
# 1. Clone / navigate to the project directory
cd AgenticPatterns_Langgraph

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your Groq API key
cp .env.example .env
# Edit .env and set GROQ_API_KEY=gsk_...

# 4. Run all 21 patterns
python main.py

# 5. Run specific patterns
python main.py --patterns 1 4 7

# 6. Run with verbose output
python main.py --patterns 5 --verbose

# 7. List all patterns
python main.py --list
```

---

## Project Structure

```
AgenticPatterns_Langgraph/
├── main.py                          # CLI entry point — runs all 21 patterns
├── requirements.txt
├── .env.example                     # Copy to .env and add GROQ_API_KEY
├── core/
│   ├── base.py                      # PatternResult dataclass + BasePattern ABC
│   └── llm.py                       # GroqLLMClient (wraps ChatGroq + raw Groq SDK)
└── patterns/
    ├── p01_prompt_chaining.py
    ├── p02_routing.py
    ├── p03_parallelization.py
    ├── p04_reflection.py
    ├── p05_tool_use.py
    ├── p06_planning.py
    ├── p07_multi_agent.py
    ├── p08_memory_management.py
    ├── p09_learning_adaptation.py
    ├── p10_model_context_protocol.py
    ├── p11_goal_setting_monitoring.py
    ├── p12_exception_handling_recovery.py
    ├── p13_human_in_the_loop.py
    ├── p14_knowledge_retrieval_rag.py
    ├── p15_inter_agent_communication.py
    ├── p16_resource_aware_optimization.py
    ├── p17_reasoning_techniques.py
    ├── p18_guardrails_safety.py
    ├── p19_evaluation_monitoring.py
    ├── p20_prioritization.py
    └── p21_exploration_discovery.py
```

---

## Architecture

### Unified Interface

Every pattern follows the same contract:

```python
from core.base import BasePattern, PatternResult

class PatternFoo(BasePattern):
    PATTERN_NUMBER = N
    PATTERN_NAME = "Pattern Name"

    def build_graph(self) -> StateGraph:
        # Construct and compile the LangGraph StateGraph
        ...

    def run(self, input_data: Any) -> PatternResult:
        # Execute and return a PatternResult
        ...
```

`PatternResult` fields:

| Field | Type | Description |
|---|---|---|
| `pattern_number` | int | 1–21 |
| `pattern_name` | str | Human-readable name |
| `success` | bool | Whether the run succeeded |
| `input_data` | Any | The input passed to `run()` |
| `output_data` | Any | Final output |
| `steps` | list | Intermediate steps/log entries |
| `execution_time_ms` | float | Wall-clock time |
| `metadata` | dict | Pattern-specific extra data |
| `error` | str\|None | Traceback if `success=False` |

### LLM Models

| Model | Use cases |
|---|---|
| `llama-3.3-70b-versatile` | Reasoning, writing, planning, multi-step analysis |
| `llama3-8b-8192` | Classification, scoring, fast single-turn calls |

---

## Pattern Reference

### 1 — Prompt Chaining
**Concept:** Sequential pipeline where each LLM call takes the previous output as input.

**Graph:** `START → outline → expand_sections → add_conclusion → copy_edit → END`

**Use cases:**
- Multi-stage content creation (research → draft → refine → publish)
- Document processing pipelines (extract → summarise → translate → format)
- Code generation pipelines (spec → architecture → implement → review)

**Demo:** Writes a technical blog post through four chained LLM calls.

---

### 2 — Routing
**Concept:** A classifier node inspects input intent and routes to a specialised handler.

**Graph:** `START → classify → [tech | creative | math | general] → END`

**Use cases:**
- Customer support ticket routing (technical / billing / general)
- Intent-based chatbot dispatch
- Multi-domain Q&A systems

**Demo:** Routes 4 different queries (tech, creative, math, general) to specialist agents.

---

### 3 — Parallelization
**Concept:** Independent analysis nodes run concurrently; results merge at an aggregator.

**Graph:** `START → fan_out → [marketing ‖ technical ‖ risk] → aggregate → END`

**Use cases:**
- Multi-perspective due diligence (legal + financial + technical)
- Parallel document analysis
- Multi-criteria product evaluation

**Demo:** Analyses a product description from three independent perspectives simultaneously.

---

### 4 — Reflection
**Concept:** Generate → critique → revise loop until quality threshold is met.

**Graph:** `START → generate → critique → [revise → critique]* → finalize → END`

**Use cases:**
- Iterative code improvement
- Essay and report quality enhancement
- Self-correcting data extraction

**Demo:** Iteratively improves a persuasive essay, stopping when quality score ≥ 8/10.

---

### 5 — Tool Use
**Concept:** LLM reasons, calls tools, incorporates results (ReAct loop).

**Tools:** `calculator`, `unit_converter`, `get_current_date`, `hotel_price_lookup`

**Use cases:**
- AI assistants that can query databases or APIs
- Automated data analysis with custom functions
- Multi-step problem solving with external computations

**Demo:** Plans a Tokyo trip by calling tools for currency conversion, hotel costs, and dates.

---

### 6 — Planning
**Concept:** Decompose a high-level goal into a step-by-step plan, then execute each step.

**Graph:** `START → create_plan → execute_step → [loop] → synthesize → END`

**Use cases:**
- Project management automation
- Code generation for complex systems
- Research task automation

**Demo:** Plans and implements a Python CPU/memory monitoring CLI tool across 5–7 steps.

---

### 7 — Multi-Agent
**Concept:** Supervisor orchestrates specialised agents (Researcher, Writer, Critic, Editor).

**Graph:** `supervisor ↔ [researcher | writer | critic | editor]`

**Use cases:**
- Automated research report generation
- Software development teams (PM → developer → reviewer)
- Content production pipelines

**Demo:** Four agents collaborate to produce a market research report on AI coding tools.

---

### 8 — Memory Management
**Concept:** Three-tier memory — short-term context window, long-term fact store, episodic summary.

**Memory tiers:**
- **Short-term:** Last N messages kept in context
- **Long-term:** Key-value fact store extracted from conversations
- **Episodic:** Compressed summaries of older turns

**Use cases:**
- Personalised AI assistants that remember user preferences
- Customer support with conversation history
- Long-running agentic workflows

**Demo:** 4-turn conversation where facts introduced in turn 1 are recalled in turns 3–4.

---

### 9 — Learning and Adaptation
**Concept:** Agent tracks strategy performance (UCB1) and adapts to use the best-scoring approach.

**Strategies:** confidence-first, evidence-first, elimination-first

**Use cases:**
- Personalised recommendation engines
- A/B testing automation
- Adaptive prompt selection

**Demo:** 6 trivia questions; agent learns which reasoning strategy scores highest and adapts.

---

### 10 — Model Context Protocol (MCP)
**Concept:** Structured registry of Resources, Tools, and Prompt Templates with token budget allocation.

**Components:** `MCPRegistry`, `MCPResource`, `MCPTool`, `MCPPromptTemplate`

**Use cases:**
- Enterprise AI integrations with multiple data sources
- Multi-system context assembly
- Reproducible, auditable AI pipelines

**Demo:** Customer support ticket resolved using context from system policy, account info, and KB articles.

---

### 11 — Goal Setting and Monitoring
**Concept:** Decompose objective into SMART goals; execute improvements; measure metrics; re-plan.

**Metrics tracked:** cyclomatic complexity, docstring coverage, bug patterns

**Use cases:**
- Automated code quality improvement
- KPI-driven business process automation
- Iterative product optimisation

**Demo:** Improves a messy Python snippet across 3 measurable quality goals.

---

### 12 — Exception Handling and Recovery
**Concept:** Detect failures, retry, use fallbacks, and degrade gracefully without crashing.

**Recovery strategies:** retry with back-off → fallback data → graceful degradation

**Use cases:**
- Robust data pipeline construction
- Production AI systems with flaky APIs
- Fault-tolerant agentic workflows

**Demo:** 3-stage sales data pipeline with injected failures demonstrating all recovery paths.

---

### 13 — Human-in-the-Loop (HITL)
**Concept:** Graph pauses at checkpoints for human review/edit before proceeding.

**Checkpoints:** subject line → email body → recipient list

**Interactive mode:** Set `INTERACTIVE_HITL=true` in `.env` to enable real `interrupt()` prompts.

**Use cases:**
- Supervised AI writing assistants
- Compliance-gated workflows
- High-stakes decision automation (legal, medical)

**Demo:** Drafts a professional email with three human approval checkpoints.

---

### 14 — Knowledge Retrieval (RAG)
**Concept:** TF-IDF cosine similarity retrieval over an in-memory corpus; augmented generation.

**Retrieval:** Pure stdlib (no external embedding API) — `collections.Counter` + `math.sqrt`

**Use cases:**
- Enterprise knowledge base Q&A
- Document-grounded chatbots
- Compliance and policy assistants

**Demo:** Answers 3 Python questions using a 10-chunk in-memory knowledge base.

---

### 15 — Inter-Agent Communication (A2A)
**Concept:** Agents publish typed messages to a shared bus; a router dispatches work based on message type.

**Message types:** `TASK`, `RESULT`, `QUERY`, `RESPONSE`, `BROADCAST`

**Agents:** Reporter → FactChecker → Editor

**Use cases:**
- Autonomous editorial pipelines
- Multi-agent software development teams
- Distributed task processing with coordination

**Demo:** Three agents collaborate to produce a fact-checked news article via message passing.

---

### 16 — Resource-Aware Optimization
**Concept:** Monitor token, cost, and latency budgets; dynamically select model tier and response depth.

**Tiers:** FULL (large model, detailed) → REDUCED (small model, concise) → MINIMAL (1 sentence)

**Use cases:**
- Cost-optimised production AI services
- Rate-limit-aware agent pipelines
- SLA-compliant response generation

**Demo:** 5 questions answered with a 1,200-token budget; strategy degrades as budget shrinks.

---

### 17 — Reasoning Techniques
**Concept:** Apply 4 reasoning strategies to the same problem; compare results.

**Techniques:** Chain-of-Thought → Tree-of-Thoughts → Self-Consistency → Least-to-Most Decomposition

**Use cases:**
- Complex mathematical problem solving
- Multi-step logical deduction
- Comparative reasoning strategy selection

**Demo:** Solves a train-speed logic puzzle using all four techniques and synthesises the best answer.

---

### 18 — Guardrails / Safety Patterns
**Concept:** Input and output validation layers detect and block harmful, injected, and PII-containing content.

**Input checks:** prompt injection, harmful intent, PII detection, semantic safety score
**Output checks:** harmful content, PII leakage, response quality

**Use cases:**
- Safe public-facing AI assistants
- Compliance-driven enterprise deployments
- Content moderation pipelines

**Demo:** Processes 6 requests (2 safe, 2 harmful, 1 injection, 1 PII-heavy); shows blocking and PII redaction.

---

### 19 — Evaluation and Monitoring
**Concept:** LLM-as-judge scores responses on 5 dimensions; auto-regenerates below threshold; builds dashboard.

**Dimensions:** Relevance, Accuracy, Coherence, Helpfulness, Safety (each 1–10)

**Use cases:**
- Automated QA for AI-generated content
- Response quality monitoring in production
- Fine-tuning data filtering

**Demo:** Evaluates 4 test cases, triggers regenerations below threshold, produces a monitoring report.

---

### 20 — Prioritization
**Concept:** Classify tasks into Eisenhower matrix quadrants; sort by weighted score; execute in optimal order.

**Formula:** `priority = urgency × 0.6 + importance × 0.4`
**Quadrants:** Q1 (do now) → Q2 (schedule) → Q3 (delegate) → Q4 (eliminate)

**Use cases:**
- AI-powered project management
- Automated ticket triage
- Resource allocation optimisation

**Demo:** 8 tasks prioritised and executed in order; Q4 tasks eliminated from the queue.

---

### 21 — Exploration and Discovery
**Concept:** Beam search over LLM-generated hypotheses; score on novelty/feasibility/impact; expand top-k.

**Parameters:** beam_width=3, max_depth=2 (configurable)

**Use cases:**
- AI-assisted ideation and brainstorming
- Research hypothesis generation
- Innovation pipeline management

**Demo:** Discovers innovative AI + sustainability product ideas through 2 rounds of beam search.

---

## Configuration

| Variable | Description | Default |
|---|---|---|
| `GROQ_API_KEY` | Your Groq API key (required) | — |
| `INTERACTIVE_HITL` | Enable real human prompts in Pattern 13 | `false` |

---

## Dependencies

| Package | Purpose |
|---|---|
| `langgraph` | Graph-based agent orchestration |
| `langchain` | LLM abstractions and tool utilities |
| `langchain-groq` | ChatGroq LangChain integration |
| `groq` | Raw Groq Python SDK |
| `python-dotenv` | Environment variable loading |
| `pydantic` | Data validation |

---

## Extending the Patterns

To add a new pattern:

1. Create `patterns/p22_your_pattern.py` following the existing template.
2. Register it in `patterns/__init__.py`.
3. Add a demo input to `DEMO_INPUTS` in `main.py`.

Each pattern is self-contained — no shared mutable state between patterns.

---

## License

MIT
