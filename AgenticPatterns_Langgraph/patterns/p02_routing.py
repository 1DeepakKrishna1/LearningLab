"""
Pattern 02: Routing
===================
Concept: A classifier node inspects the incoming query, determines its category,
and routes it to one of several specialized handler nodes — each with its own
system prompt and processing logic.

Graph:  START → classify → [tech | creative | math | general] → END

Demo:   Route four different user queries to the appropriate specialist agent.
"""
from __future__ import annotations

import traceback

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL


class RouterState(TypedDict):
    query: str
    route: str          # "tech" | "creative" | "math" | "general"
    confidence: float
    routing_rationale: str
    response: str


SPECIALIST_PROMPTS: dict[str, str] = {
    "tech": (
        "You are a senior software engineer and technical expert. "
        "Provide precise, accurate technical answers with code examples where useful."
    ),
    "creative": (
        "You are a creative writing coach and storytelling expert. "
        "Respond with imagination, vivid language, and structured narrative."
    ),
    "math": (
        "You are a mathematics professor. "
        "Work through problems step-by-step, showing all reasoning clearly."
    ),
    "general": (
        "You are a knowledgeable assistant covering a broad range of topics. "
        "Provide clear, well-organised answers."
    ),
}


class PatternRouting(BasePattern):
    PATTERN_NUMBER = 2
    PATTERN_NAME = "Routing"
    DESCRIPTION = (
        "Classify input intent and route to a specialised handler node."
    )

    # ------------------------------------------------------------------ nodes

    def _classify(self, state: RouterState) -> dict:
        prompt = (
            "Classify the following user query into exactly one category:\n"
            "- tech   : programming, software, hardware, technology questions\n"
            "- creative: writing, storytelling, poetry, creative tasks\n"
            "- math   : mathematics, statistics, logic puzzles\n"
            "- general: anything else\n\n"
            f"Query: {state['query']}\n\n"
            "Respond in this exact JSON format (no other text):\n"
            '{"route": "<category>", "confidence": <0.0-1.0>, "rationale": "<one sentence>"}'
        )
        raw = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=128)

        import json, re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                route = data.get("route", "general").strip().lower()
                if route not in SPECIALIST_PROMPTS:
                    route = "general"
                return {
                    "route": route,
                    "confidence": float(data.get("confidence", 0.8)),
                    "routing_rationale": data.get("rationale", ""),
                }
            except json.JSONDecodeError:
                pass

        # Fallback: keyword-based routing
        q = state["query"].lower()
        if any(k in q for k in ("code", "python", "error", "bug", "api", "server")):
            route = "tech"
        elif any(k in q for k in ("write", "story", "poem", "creative")):
            route = "creative"
        elif any(k in q for k in ("calculate", "solve", "math", "equation", "how many")):
            route = "math"
        else:
            route = "general"
        return {"route": route, "confidence": 0.6, "routing_rationale": "keyword fallback"}

    def _route_fn(self, state: RouterState) -> str:
        return state["route"]

    def _handle_tech(self, state: RouterState) -> dict:
        return {"response": self.llm.chat(
            [{"role": "user", "content": state["query"]}],
            system=SPECIALIST_PROMPTS["tech"],
            model=MODEL_LARGE,
            max_tokens=600,
        )}

    def _handle_creative(self, state: RouterState) -> dict:
        return {"response": self.llm.chat(
            [{"role": "user", "content": state["query"]}],
            system=SPECIALIST_PROMPTS["creative"],
            model=MODEL_LARGE,
            max_tokens=600,
        )}

    def _handle_math(self, state: RouterState) -> dict:
        return {"response": self.llm.chat(
            [{"role": "user", "content": state["query"]}],
            system=SPECIALIST_PROMPTS["math"],
            model=MODEL_LARGE,
            max_tokens=600,
        )}

    def _handle_general(self, state: RouterState) -> dict:
        return {"response": self.llm.chat(
            [{"role": "user", "content": state["query"]}],
            system=SPECIALIST_PROMPTS["general"],
            model=MODEL_LARGE,
            max_tokens=600,
        )}

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(RouterState)
        graph.add_node("classify", self._classify)
        graph.add_node("tech", self._handle_tech)
        graph.add_node("creative", self._handle_creative)
        graph.add_node("math", self._handle_math)
        graph.add_node("general", self._handle_general)

        graph.add_edge(START, "classify")
        graph.add_conditional_edges(
            "classify",
            self._route_fn,
            {"tech": "tech", "creative": "creative", "math": "math", "general": "general"},
        )
        for node in ("tech", "creative", "math", "general"):
            graph.add_edge(node, END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        """
        input_data can be a single query string or a list of query strings.
        When a list is provided, each query is routed and all results returned.
        """
        try:
            app = self.build_graph()
            queries = input_data if isinstance(input_data, list) else [input_data]
            all_results = []

            total_elapsed = 0.0
            for query in queries:
                state: RouterState = {
                    "query": query,
                    "route": "",
                    "confidence": 0.0,
                    "routing_rationale": "",
                    "response": "",
                }
                final, elapsed_ms = self._timed_run(app.invoke, state)
                total_elapsed += elapsed_ms
                all_results.append({
                    "query": query,
                    "route": final["route"],
                    "confidence": final["confidence"],
                    "rationale": final["routing_rationale"],
                    "response": final["response"],
                })

            output = (
                all_results[0]["response"]
                if len(all_results) == 1
                else all_results
            )
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=output,
                elapsed_ms=total_elapsed,
                steps=[{"query": r["query"], "route": r["route"], "confidence": r["confidence"]} for r in all_results],
                metadata={"routes": [r["route"] for r in all_results]},
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
