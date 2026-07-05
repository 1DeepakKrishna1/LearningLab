"""
FastAPI server exposing all 21 Agentic Patterns as REST endpoints.

Run from the project root:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import dataclasses
import os
import sys
from datetime import date, datetime
from enum import Enum
from typing import Any

# Allow imports from project root (llm_client, patterns)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from llm_client import GroqClient  # noqa: E402
from patterns import (  # noqa: E402
    EvaluationMonitoringPattern,
    ExceptionRecoveryPattern,
    ExplorationDiscoveryPattern,
    GoalMonitoringPattern,
    GuardrailsSafetyPattern,
    HumanInTheLoopPattern,
    InterAgentCommunicationPattern,
    KnowledgeRetrievalPattern,
    LearningAdaptationPattern,
    MemoryManagementPattern,
    ModelContextProtocolPattern,
    MultiAgentPattern,
    ParallelizationPattern,
    PlanningPattern,
    PrioritizationPattern,
    PromptChainingPattern,
    ReasoningTechniquesPattern,
    ReflectionPattern,
    ResourceOptimizationPattern,
    RoutingPattern,
    ToolUsePattern,
)

# ---------------------------------------------------------------------------
# Serialisation helper
# ---------------------------------------------------------------------------


def safe_serialize(obj: Any) -> Any:
    """Recursively convert any Python object to a JSON-serialisable form."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            f.name: safe_serialize(getattr(obj, f.name))
            for f in dataclasses.fields(obj)
        }
    if isinstance(obj, dict):
        return {str(k): safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [safe_serialize(i) for i in obj]
    if hasattr(obj, "__dict__"):
        return {
            k: safe_serialize(v)
            for k, v in vars(obj).items()
            if not k.startswith("_")
        }
    return str(obj)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agentic Patterns API",
    description="REST API exposing all 21 Agentic AI Design Patterns",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _client() -> GroqClient:
    return GroqClient()


# ---------------------------------------------------------------------------
# Pattern metadata (drives both the /api/patterns listing and the React UI)
# ---------------------------------------------------------------------------

PATTERNS_META: list[dict] = [
    {
        "id": 1,
        "name": "Prompt Chaining",
        "description": "Sequential pipeline where the output of each LLM call becomes the input for the next, progressively refining content.",
        "category": "Core",
        "fields": [
            {
                "name": "topic",
                "label": "Topic",
                "type": "text",
                "default": "The impact of AI on software engineering",
                "required": True,
            },
        ],
    },
    {
        "id": 2,
        "name": "Routing",
        "description": "Classify a query and route it to the most appropriate specialist handler (technical, creative, analytical, or general).",
        "category": "Core",
        "fields": [
            {
                "name": "query",
                "label": "Query",
                "type": "text",
                "default": "Explain how transformer neural networks work",
                "required": True,
            },
        ],
    },
    {
        "id": 3,
        "name": "Parallelization",
        "description": "Fan-out multiple independent LLM calls concurrently across different perspectives, then synthesise the results.",
        "category": "Core",
        "fields": [
            {
                "name": "topic",
                "label": "Topic",
                "type": "text",
                "default": "Large Language Models replacing software developers",
                "required": True,
            },
        ],
    },
    {
        "id": 4,
        "name": "Reflection",
        "description": "Generate code, critique it, then iteratively improve through N reflection loops.",
        "category": "Core",
        "fields": [
            {
                "name": "task",
                "label": "Task",
                "type": "text",
                "default": "Write a Python function using Sieve of Eratosthenes",
                "required": True,
            },
            {
                "name": "iterations",
                "label": "Iterations",
                "type": "number",
                "default": 2,
                "min": 1,
                "max": 4,
            },
        ],
    },
    {
        "id": 5,
        "name": "Tool Use",
        "description": "Agent autonomously decides which tools to invoke (calculator, date, unit converter, word counter) and loops until done.",
        "category": "Core",
        "fields": [
            {
                "name": "query",
                "label": "Query",
                "type": "text",
                "default": "What is 15 squared plus the square root of 2025? Convert the result to miles. What is today's date?",
                "required": True,
            },
            {
                "name": "max_tool_rounds",
                "label": "Max Tool Rounds",
                "type": "number",
                "default": 8,
                "min": 1,
                "max": 10,
            },
        ],
    },
    {
        "id": 6,
        "name": "Planning",
        "description": "Decompose a complex goal into 3–5 steps, execute each sequentially with accumulated context, then consolidate.",
        "category": "Core",
        "fields": [
            {
                "name": "goal",
                "label": "Goal",
                "type": "textarea",
                "default": "Create a go-to-market strategy for an AI-powered code review SaaS product",
                "required": True,
            },
        ],
    },
    {
        "id": 7,
        "name": "Multi-Agent",
        "description": "Orchestrator + Researcher + Writer + Reviewer agents collaborate via a sequential pipeline to produce a polished article.",
        "category": "Core",
        "fields": [
            {
                "name": "topic",
                "label": "Topic",
                "type": "text",
                "default": "The future of AI-assisted software development by 2030",
                "required": True,
            },
        ],
    },
    {
        "id": 8,
        "name": "Memory Management",
        "description": "Dual-layer memory (short-term rolling buffer + long-term key-value store) persists facts across conversation turns.",
        "category": "Extended",
        "fields": [
            {
                "name": "turns",
                "label": "Conversation Turns (one per line)",
                "type": "textarea",
                "default": "Hi! I'm Alex, a Python developer working on backend services.\nWhat frameworks should I use for async work?\nI'm also learning Rust on the side.\nCan you summarise what you know about me?",
                "required": False,
            },
        ],
    },
    {
        "id": 9,
        "name": "Learning & Adaptation",
        "description": "Agent observes feedback ratings and comments, updates a preference profile, and adapts its response style on subsequent rounds.",
        "category": "Extended",
        "fields": [
            {
                "name": "prompt",
                "label": "Prompt",
                "type": "text",
                "default": "Explain recursion in programming.",
                "required": True,
            },
        ],
    },
    {
        "id": 10,
        "name": "Model Context Protocol",
        "description": "Simulates MCP (JSON-RPC 2.0) for standardised tool/resource/prompt discovery — an implementation of Anthropic's MCP spec.",
        "category": "Extended",
        "fields": [
            {
                "name": "query",
                "label": "Query",
                "type": "text",
                "default": "What products does our company offer and what is today's date?",
                "required": True,
            },
        ],
    },
    {
        "id": 11,
        "name": "Goal Monitoring",
        "description": "Decompose a goal into SMART milestones, execute each, assess progress 0–100%, detect blockers, and generate a report.",
        "category": "Extended",
        "fields": [
            {
                "name": "goal_title",
                "label": "Goal Title",
                "type": "text",
                "default": "Launch an open-source Python library for LLM prompt management",
                "required": True,
            },
            {
                "name": "goal_description",
                "label": "Goal Description",
                "type": "textarea",
                "default": "Build a production-ready library with templating, versioning, and A/B testing for LLM prompts",
                "required": False,
            },
        ],
    },
    {
        "id": 12,
        "name": "Exception Recovery",
        "description": "Layered recovery chain handles failures via retry with back-off, prompt simplification, model fallback, and graceful degradation.",
        "category": "Extended",
        "fields": [
            {
                "name": "prompt",
                "label": "Prompt",
                "type": "text",
                "default": "Explain CAP theorem",
                "required": True,
            },
        ],
    },
    {
        "id": 13,
        "name": "Human in the Loop",
        "description": "Insert APPROVE/MODIFY/INFORM checkpoints where the agent auto-pauses before proceeding (non-interactive demo mode).",
        "category": "Extended",
        "fields": [
            {
                "name": "topic",
                "label": "Topic",
                "type": "text",
                "default": "Best practices for securing REST APIs",
                "required": True,
            },
        ],
    },
    {
        "id": 14,
        "name": "Knowledge Retrieval (RAG)",
        "description": "BM25 retrieval pipeline grounds LLM responses in 3 authoritative security documents to reduce hallucinations.",
        "category": "Extended",
        "fields": [
            {
                "name": "questions",
                "label": "Questions (one per line)",
                "type": "textarea",
                "default": "What are the improvements in TLS 1.3?\nHow do I prevent SQL injection?\nWhat is mutual TLS authentication?",
                "required": False,
            },
        ],
    },
    {
        "id": 15,
        "name": "Inter-Agent Communication",
        "description": "Distributed agents communicate via A2A typed message protocol (REQUEST/RESPONSE/BROADCAST/HANDOFF) through a central registry.",
        "category": "Advanced",
        "fields": [
            {
                "name": "topic",
                "label": "Topic",
                "type": "text",
                "default": "Zero-trust security architecture for cloud-native applications",
                "required": True,
            },
        ],
    },
    {
        "id": 16,
        "name": "Resource Optimization",
        "description": "Agent monitors token/call/cost budget and dynamically switches model/quality strategy to stay within limits.",
        "category": "Advanced",
        "fields": [
            {
                "name": "token_limit",
                "label": "Token Limit",
                "type": "number",
                "default": 5000,
                "min": 1000,
                "max": 20000,
            },
            {
                "name": "call_limit",
                "label": "API Call Limit",
                "type": "number",
                "default": 8,
                "min": 2,
                "max": 20,
            },
        ],
    },
    {
        "id": 17,
        "name": "Reasoning Techniques",
        "description": "Compare Chain-of-Thought, Tree-of-Thought, ReAct (Reason+Act), and Self-Consistency on the same reasoning problem.",
        "category": "Advanced",
        "fields": [
            {
                "name": "problem",
                "label": "Problem",
                "type": "textarea",
                "default": "A train travels from A to B at 60 km/h and returns at 40 km/h. What is the average speed for the entire round trip?",
                "required": True,
            },
        ],
    },
    {
        "id": 18,
        "name": "Guardrails & Safety",
        "description": "Multi-layer guardrails scan input/output for PII, prompt injection, policy violations, and harmful content.",
        "category": "Advanced",
        "fields": [
            {
                "name": "test_input",
                "label": "Text to Evaluate",
                "type": "textarea",
                "default": "Hello! Can you explain how HTTPS encryption works and why it is important for web security?",
                "required": False,
            },
        ],
    },
    {
        "id": 19,
        "name": "Evaluation & Monitoring",
        "description": "Continuous quality measurement via LLM judge (5 dimensions), A/B comparison, and drift monitoring.",
        "category": "Advanced",
        "fields": [
            {
                "name": "test_prompts",
                "label": "Test Prompts (one per line — leave empty for built-in defaults)",
                "type": "textarea",
                "default": "",
                "required": False,
            },
        ],
    },
    {
        "id": 20,
        "name": "Prioritization",
        "description": "Multi-framework task prioritisation using Eisenhower Matrix, RICE scoring, and optional LLM triage on a demo backlog.",
        "category": "Advanced",
        "fields": [
            {
                "name": "use_llm_triage",
                "label": "Use LLM Triage",
                "type": "boolean",
                "default": True,
            },
        ],
    },
    {
        "id": 21,
        "name": "Exploration & Discovery",
        "description": "Autonomous knowledge graph expansion — starts from a seed concept and discovers related topics via configurable BFS/DFS/best-first search.",
        "category": "Advanced",
        "fields": [
            {
                "name": "seed",
                "label": "Seed Concept",
                "type": "text",
                "default": "Zero-Knowledge Proofs",
                "required": True,
            },
            {
                "name": "strategy",
                "label": "Search Strategy",
                "type": "select",
                "default": "bfs",
                "options": ["bfs", "dfs", "best_first"],
            },
            {
                "name": "max_depth",
                "label": "Max Depth",
                "type": "number",
                "default": 2,
                "min": 1,
                "max": 4,
            },
            {
                "name": "max_nodes",
                "label": "Max Nodes",
                "type": "number",
                "default": 8,
                "min": 4,
                "max": 15,
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Listing endpoint
# ---------------------------------------------------------------------------


@app.get("/api/patterns")
def list_patterns() -> dict:
    return {"patterns": PATTERNS_META}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Pattern dispatch
# ---------------------------------------------------------------------------


async def _dispatch(pattern_id: int, body: dict) -> Any:  # noqa: C901
    client = _client()

    if pattern_id == 1:
        p = PromptChainingPattern(client)
        return await p.run(
            topic=body.get("topic", "The impact of AI on software engineering")
        )

    if pattern_id == 2:
        p = RoutingPattern(client)
        return await p.run(
            query=body.get("query", "Explain how transformer neural networks work")
        )

    if pattern_id == 3:
        p = ParallelizationPattern(client)
        return await p.run(
            topic=body.get("topic", "Large Language Models replacing software developers")
        )

    if pattern_id == 4:
        p = ReflectionPattern(client)
        return await p.run(
            task=body.get("task", "Write a Python function using Sieve of Eratosthenes"),
            iterations=int(body.get("iterations", 2)),
        )

    if pattern_id == 5:
        p = ToolUsePattern(client)
        return await p.run(
            query=body.get(
                "query",
                "What is 15 squared plus the square root of 2025? Convert the result to miles. What is today's date?",
            ),
            max_tool_rounds=int(body.get("max_tool_rounds", 8)),
        )

    if pattern_id == 6:
        p = PlanningPattern(client)
        return await p.run(
            goal=body.get(
                "goal",
                "Create a go-to-market strategy for an AI-powered code review SaaS product",
            )
        )

    if pattern_id == 7:
        p = MultiAgentPattern(client)
        return await p.run(
            topic=body.get("topic", "The future of AI-assisted software development by 2030")
        )

    if pattern_id == 8:
        p = MemoryManagementPattern(client)
        raw = body.get("turns", "")
        if isinstance(raw, str):
            turns = [t.strip() for t in raw.splitlines() if t.strip()] or None
        else:
            turns = raw or None
        return await p.run(turns=turns)

    if pattern_id == 9:
        p = LearningAdaptationPattern(client)
        return await p.run(prompt=body.get("prompt", "Explain recursion in programming."))

    if pattern_id == 10:
        p = ModelContextProtocolPattern(client)
        return await p.run(
            query=body.get(
                "query", "What products does our company offer and what is today's date?"
            )
        )

    if pattern_id == 11:
        p = GoalMonitoringPattern(client)
        return await p.run(
            goal_title=body.get(
                "goal_title", "Launch an open-source Python library for LLM prompt management"
            ),
            goal_description=body.get(
                "goal_description",
                "Build a production-ready library with templating, versioning, and A/B testing for LLM prompts",
            ),
        )

    if pattern_id == 12:
        p = ExceptionRecoveryPattern(client)
        return await p.run(prompt=body.get("prompt", "Explain CAP theorem"))

    if pattern_id == 13:
        p = HumanInTheLoopPattern(client)
        return await p.run(
            topic=body.get("topic", "Best practices for securing REST APIs"),
            interactive=False,
        )

    if pattern_id == 14:
        p = KnowledgeRetrievalPattern(client)
        raw = body.get("questions", "")
        if isinstance(raw, str):
            questions = [q.strip() for q in raw.splitlines() if q.strip()] or None
        else:
            questions = raw or None
        return await p.run(questions=questions)

    if pattern_id == 15:
        p = InterAgentCommunicationPattern(client)
        return await p.run(
            topic=body.get("topic", "Zero-trust security architecture for cloud-native applications")
        )

    if pattern_id == 16:
        p = ResourceOptimizationPattern(client)
        return await p.run(
            token_limit=int(body.get("token_limit", 5000)),
            call_limit=int(body.get("call_limit", 8)),
        )

    if pattern_id == 17:
        p = ReasoningTechniquesPattern(client)
        return await p.run(
            problem=body.get(
                "problem",
                "A train travels from A to B at 60 km/h and returns at 40 km/h. What is the average speed for the entire round trip?",
            )
        )

    if pattern_id == 18:
        p = GuardrailsSafetyPattern(client)
        test_input: str = body.get("test_input", "")
        test_cases = [("user_input", test_input)] if test_input.strip() else None
        return await p.run(test_cases=test_cases)

    if pattern_id == 19:
        p = EvaluationMonitoringPattern(client)
        raw = body.get("test_prompts", "")
        if isinstance(raw, str):
            prompts = [line.strip() for line in raw.splitlines() if line.strip()]
        else:
            prompts = list(raw or [])
        test_suite = [(pr, "default") for pr in prompts] if prompts else None
        return await p.run(test_suite=test_suite)

    if pattern_id == 20:
        p = PrioritizationPattern(client)
        return await p.run(use_llm_triage=bool(body.get("use_llm_triage", True)))

    if pattern_id == 21:
        p = ExplorationDiscoveryPattern(client)
        return await p.run(
            seed=body.get("seed", "Zero-Knowledge Proofs"),
            strategy=body.get("strategy", "bfs"),
            max_depth=int(body.get("max_depth", 2)),
            max_nodes=int(body.get("max_nodes", 8)),
        )

    raise HTTPException(status_code=404, detail=f"Pattern {pattern_id} not found")


@app.post("/api/patterns/{pattern_id}/run")
async def run_pattern(pattern_id: int, request: Request) -> dict:
    try:
        body: dict = await request.json()
    except Exception:
        body = {}

    try:
        result = await _dispatch(pattern_id, body)
        return {"pattern_id": pattern_id, "result": safe_serialize(result)}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
