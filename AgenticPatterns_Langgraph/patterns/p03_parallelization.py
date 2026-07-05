"""
Pattern 03: Parallelization
============================
Concept: Multiple independent analysis nodes execute simultaneously (LangGraph
executes branches with no inter-dependencies in parallel). An aggregator node
merges results when all branches complete.

Graph:  START → fan_out → [marketing_analyst ‖ tech_analyst ‖ risk_analyst]
                        → aggregate → END

Note: LangGraph detects that marketing_analyst, tech_analyst, and risk_analyst
      all depend only on fan_out (no mutual dependencies) and runs them
      concurrently. The `branches_done` field uses the `operator.add` reducer
      so each branch can safely append its tag without overwriting the others.

Demo:   Analyse a product description from three parallel perspectives then
        synthesise a complete profile.
"""
from __future__ import annotations

import traceback
from typing import Annotated, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL


class ParallelState(TypedDict):
    product_description: str
    marketing_angle: str
    technical_summary: str
    risk_assessment: str
    combined_profile: str
    branches_done: Annotated[List[str], operator.add]   # reducer: safe concurrent append


class PatternParallelization(BasePattern):
    PATTERN_NUMBER = 3
    PATTERN_NAME = "Parallelization"
    DESCRIPTION = (
        "Fan-out to independent analysis nodes running in parallel; "
        "fan-in to an aggregator."
    )

    # ------------------------------------------------------------------ nodes

    def _fan_out(self, state: ParallelState) -> dict:
        # No-op fan-out node; exists solely to give LangGraph a single
        # origin point so it can detect the three-way parallel branch.
        return {}

    def _marketing_analyst(self, state: ParallelState) -> dict:
        prompt = (
            "You are a senior marketing strategist.\n"
            f"Product: {state['product_description']}\n\n"
            "Write a 120-word marketing analysis covering: target audience, "
            "key selling points, and positioning statement."
        )
        result = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=256)
        return {
            "marketing_angle": result,
            "branches_done": ["marketing"],
        }

    def _tech_analyst(self, state: ParallelState) -> dict:
        prompt = (
            "You are a principal engineer.\n"
            f"Product: {state['product_description']}\n\n"
            "Write a 120-word technical summary covering: architecture assumptions, "
            "scalability considerations, and technology stack."
        )
        result = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=256)
        return {
            "technical_summary": result,
            "branches_done": ["technical"],
        }

    def _risk_analyst(self, state: ParallelState) -> dict:
        prompt = (
            "You are a risk and compliance analyst.\n"
            f"Product: {state['product_description']}\n\n"
            "Write a 120-word risk assessment covering: top 3 business risks, "
            "mitigation strategies, and compliance considerations."
        )
        result = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=256)
        return {
            "risk_assessment": result,
            "branches_done": ["risk"],
        }

    def _aggregate(self, state: ParallelState) -> dict:
        prompt = (
            "Synthesise the three analyses below into a concise executive product profile "
            "(≤250 words).\n\n"
            f"## Marketing Analysis\n{state['marketing_angle']}\n\n"
            f"## Technical Summary\n{state['technical_summary']}\n\n"
            f"## Risk Assessment\n{state['risk_assessment']}\n\n"
            "Executive Product Profile:"
        )
        combined = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=512)
        return {"combined_profile": combined}

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(ParallelState)

        graph.add_node("fan_out", self._fan_out)
        graph.add_node("marketing_analyst", self._marketing_analyst)
        graph.add_node("tech_analyst", self._tech_analyst)
        graph.add_node("risk_analyst", self._risk_analyst)
        graph.add_node("aggregate", self._aggregate)

        graph.add_edge(START, "fan_out")
        # Three edges from fan_out → parallel execution
        graph.add_edge("fan_out", "marketing_analyst")
        graph.add_edge("fan_out", "tech_analyst")
        graph.add_edge("fan_out", "risk_analyst")
        # All three converge at aggregate
        graph.add_edge("marketing_analyst", "aggregate")
        graph.add_edge("tech_analyst", "aggregate")
        graph.add_edge("risk_analyst", "aggregate")
        graph.add_edge("aggregate", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial: ParallelState = {
                "product_description": input_data,
                "marketing_angle": "",
                "technical_summary": "",
                "risk_assessment": "",
                "combined_profile": "",
                "branches_done": [],
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            steps = [
                {"branch": b, "completed": True} for b in final["branches_done"]
            ] + [{"branch": "aggregate", "completed": True}]
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["combined_profile"],
                elapsed_ms=elapsed_ms,
                steps=steps,
                metadata={
                    "branches_completed": final["branches_done"],
                    "marketing_angle": final["marketing_angle"][:200],
                    "technical_summary": final["technical_summary"][:200],
                    "risk_assessment": final["risk_assessment"][:200],
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
