"""
Pattern 01: Prompt Chaining
===========================
Concept: The output of one LLM call becomes the structured input of the next,
forming a sequential pipeline where each step refines or extends the prior result.

Graph:  START → outline → expand_sections → add_conclusion → copy_edit → END

Demo:   "Write a technical blog post about quantum computing"
"""
from __future__ import annotations

import traceback
from typing import Annotated, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE


class ChainState(TypedDict):
    topic: str
    outline: str
    expanded_sections: str
    conclusion: str
    final_post: str
    steps_log: Annotated[List[str], operator.add]


class PatternPromptChaining(BasePattern):
    PATTERN_NUMBER = 1
    PATTERN_NAME = "Prompt Chaining"
    DESCRIPTION = (
        "Sequential pipeline where each LLM call builds on the previous output."
    )

    # ------------------------------------------------------------------ nodes

    def _generate_outline(self, state: ChainState) -> dict:
        prompt = (
            f"Create a detailed outline for a technical blog post titled:\n"
            f"'{state['topic']}'\n\n"
            f"Include 4 main sections with 2-3 sub-points each. "
            f"Format as a numbered list."
        )
        outline = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=512)
        return {
            "outline": outline,
            "steps_log": [f"Step 1 — Outline generated ({len(outline)} chars)"],
        }

    def _expand_sections(self, state: ChainState) -> dict:
        prompt = (
            f"Using this outline:\n{state['outline']}\n\n"
            f"Write the introduction and first two sections of the blog post "
            f"about '{state['topic']}'. Be technical yet accessible. ~400 words."
        )
        expanded = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=800)
        return {
            "expanded_sections": expanded,
            "steps_log": [f"Step 2 — Sections expanded ({len(expanded)} chars)"],
        }

    def _add_conclusion(self, state: ChainState) -> dict:
        prompt = (
            f"Given this partial blog post:\n{state['expanded_sections']}\n\n"
            f"Write a compelling conclusion for the blog post about "
            f"'{state['topic']}'. Include 2-3 key takeaways and a call to action. "
            f"~150 words."
        )
        conclusion = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=400)
        return {
            "conclusion": conclusion,
            "steps_log": [f"Step 3 — Conclusion added ({len(conclusion)} chars)"],
        }

    def _copy_edit(self, state: ChainState) -> dict:
        full_draft = (
            f"{state['expanded_sections']}\n\n## Conclusion\n{state['conclusion']}"
        )
        prompt = (
            f"Copy-edit the following blog post for clarity, flow, and grammar. "
            f"Fix any awkward phrasing. Keep the technical depth. Return the full "
            f"polished post:\n\n{full_draft}"
        )
        final = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=1500)
        return {
            "final_post": final,
            "steps_log": [f"Step 4 — Copy-editing complete ({len(final)} chars)"],
        }

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(ChainState)
        graph.add_node("outline", self._generate_outline)
        graph.add_node("expand_sections", self._expand_sections)
        graph.add_node("add_conclusion", self._add_conclusion)
        graph.add_node("copy_edit", self._copy_edit)

        graph.add_edge(START, "outline")
        graph.add_edge("outline", "expand_sections")
        graph.add_edge("expand_sections", "add_conclusion")
        graph.add_edge("add_conclusion", "copy_edit")
        graph.add_edge("copy_edit", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial_state: ChainState = {
                "topic": input_data,
                "outline": "",
                "expanded_sections": "",
                "conclusion": "",
                "final_post": "",
                "steps_log": [],
            }
            final_state, elapsed_ms = self._timed_run(
                app.invoke, initial_state
            )
            steps = [{"step": i + 1, "log": s} for i, s in enumerate(final_state["steps_log"])]
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final_state["final_post"],
                elapsed_ms=elapsed_ms,
                steps=steps,
                metadata={
                    "outline": final_state["outline"],
                    "pipeline_stages": 4,
                },
            )
        except Exception as exc:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
