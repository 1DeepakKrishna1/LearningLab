"""
Pattern 04: Reflection
======================
Concept: The agent generates a draft, critiques it, then revises — iterating
until a quality threshold is met or the maximum iteration count is reached.

Graph:  START → generate → critique → [revise → critique (loop)] → finalize → END

Demo:   Iteratively improve a persuasive essay on renewable energy.
"""
from __future__ import annotations

import re
import traceback
from typing import Annotated, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE

QUALITY_THRESHOLD = 8   # 1-10 scale; stop iterating when reached
MAX_REVISIONS = 3


class ReflectionState(TypedDict):
    task: str
    draft: str
    critique: str
    quality_score: int
    revision_count: int
    max_revisions: int
    history: Annotated[List[Dict], operator.add]


class PatternReflection(BasePattern):
    PATTERN_NUMBER = 4
    PATTERN_NAME = "Reflection"
    DESCRIPTION = (
        "Generate → critique → revise loop until quality threshold is met."
    )

    # ------------------------------------------------------------------ nodes

    def _generate_draft(self, state: ReflectionState) -> dict:
        if state["draft"]:
            # Revision pass: use critique as guidance
            prompt = (
                f"Task: {state['task']}\n\n"
                f"Previous draft:\n{state['draft']}\n\n"
                f"Critique to address:\n{state['critique']}\n\n"
                "Write an improved version that addresses all critique points. "
                "Be thorough and persuasive."
            )
        else:
            prompt = (
                f"Write a persuasive, well-structured argument for the following task:\n"
                f"{state['task']}\n\n"
                "Use clear structure: introduction, 3 supporting arguments, conclusion. "
                "~300 words."
            )
        draft = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=700)
        return {
            "draft": draft,
            "history": [{"revision": state["revision_count"], "type": "draft", "length": len(draft)}],
        }

    def _critique(self, state: ReflectionState) -> dict:
        prompt = (
            "You are a strict editor. Evaluate the following draft on:\n"
            "1. Argument strength (is the logic sound?)\n"
            "2. Evidence quality (are claims supported?)\n"
            "3. Clarity and flow\n"
            "4. Persuasiveness\n\n"
            f"Draft:\n{state['draft']}\n\n"
            "First, list specific weaknesses. Then on a NEW line write:\n"
            "QUALITY_SCORE: <integer 1-10>\n"
            "(10 = publication-ready, 1 = needs complete rewrite)"
        )
        critique_text = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=400)

        # Parse quality score
        match = re.search(r"QUALITY_SCORE:\s*(\d+)", critique_text, re.IGNORECASE)
        score = int(match.group(1)) if match else 6
        score = max(1, min(10, score))

        return {
            "critique": critique_text,
            "quality_score": score,
            "history": [{"revision": state["revision_count"], "type": "critique", "score": score}],
        }

    def _revise(self, state: ReflectionState) -> dict:
        return {
            "revision_count": state["revision_count"] + 1,
            "history": [{"revision": state["revision_count"] + 1, "type": "revision_started"}],
        }

    def _finalize(self, state: ReflectionState) -> dict:
        return {
            "history": [{
                "type": "finalized",
                "final_score": state["quality_score"],
                "total_revisions": state["revision_count"],
            }]
        }

    def _should_continue(self, state: ReflectionState) -> str:
        if (
            state["quality_score"] < QUALITY_THRESHOLD
            and state["revision_count"] < state["max_revisions"]
        ):
            return "revise"
        return "finalize"

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(ReflectionState)

        graph.add_node("generate_draft", self._generate_draft)
        graph.add_node("critique", self._critique)
        graph.add_node("revise", self._revise)
        graph.add_node("finalize", self._finalize)

        graph.add_edge(START, "generate_draft")
        graph.add_edge("generate_draft", "critique")
        graph.add_conditional_edges(
            "critique",
            self._should_continue,
            {"revise": "revise", "finalize": "finalize"},
        )
        # After revise, regenerate the draft with critique guidance
        graph.add_edge("revise", "generate_draft")
        graph.add_edge("finalize", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial: ReflectionState = {
                "task": input_data,
                "draft": "",
                "critique": "",
                "quality_score": 0,
                "revision_count": 0,
                "max_revisions": kwargs.get("max_revisions", MAX_REVISIONS),
                "history": [],
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["draft"],
                elapsed_ms=elapsed_ms,
                steps=final["history"],
                metadata={
                    "final_quality_score": final["quality_score"],
                    "total_revisions": final["revision_count"],
                    "quality_threshold": QUALITY_THRESHOLD,
                    "last_critique": final["critique"][:300],
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
