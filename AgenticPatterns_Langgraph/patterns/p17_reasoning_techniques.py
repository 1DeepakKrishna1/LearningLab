"""
Pattern 17: Reasoning Techniques
===================================
Concept: Apply three distinct reasoning strategies to the same problem and
compare results. Demonstrates when each approach excels.

Techniques:
  1. Chain-of-Thought (CoT)       — step-by-step linear reasoning
  2. Tree-of-Thoughts (ToT)       — branch multiple hypotheses, evaluate, prune
  3. Self-Consistency (SC)        — sample N solutions, majority-vote the answer
  4. Least-to-Most Decomposition  — break into simpler sub-problems, solve bottom-up

Graph:  START → cot_reasoning → tot_reasoning → self_consistency → least_to_most
              → compare_techniques → END

Demo:   Multi-step logic puzzle: "A train leaves City A at 60 km/h. Another leaves
        City B (300 km away) towards City A at 90 km/h. Where do they meet?"
        + A coding problem to showcase least-to-most.
"""
from __future__ import annotations

import re
import traceback
from typing import Annotated, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL

DEMO_PROBLEM = (
    "A train leaves City A at 60 km/h. "
    "Another train leaves City B, which is 300 km away, heading towards City A at 90 km/h. "
    "Both trains depart at the same time. "
    "At what distance from City A do they meet, and how long does it take?"
)


class ReasoningState(TypedDict):
    problem: str
    cot_answer: str
    cot_trace: str
    tot_candidates: List[str]
    tot_answer: str
    tot_trace: str
    sc_samples: List[str]
    sc_answer: str
    ltm_subproblems: List[str]
    ltm_answer: str
    technique_results: Dict[str, str]
    comparison: str
    final_answer: str


class PatternReasoningTechniques(BasePattern):
    PATTERN_NUMBER = 17
    PATTERN_NAME = "Reasoning Techniques"
    DESCRIPTION = (
        "CoT, Tree-of-Thoughts, Self-Consistency, Least-to-Most — applied and compared."
    )

    # ------------------------------------------------------------------ nodes

    def _cot_reasoning(self, state: ReasoningState) -> dict:
        """Chain-of-Thought: explicit step-by-step reasoning."""
        prompt = (
            "Solve the following problem step by step. Show every calculation explicitly.\n\n"
            f"Problem: {state['problem']}\n\n"
            "Format your response as:\n"
            "STEP 1: [describe what you're solving]\n"
            "STEP 2: [next step]\n"
            "...\n"
            "ANSWER: [final answer]"
        )
        trace = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=500)

        match = re.search(r"ANSWER:\s*(.+?)(?:\n|$)", trace, re.IGNORECASE | re.DOTALL)
        answer = match.group(1).strip() if match else trace.split("\n")[-1].strip()

        return {
            "cot_trace": trace,
            "cot_answer": answer,
            "technique_results": {"chain_of_thought": answer},
        }

    def _tot_reasoning(self, state: ReasoningState) -> dict:
        """Tree-of-Thoughts: generate multiple solution paths, evaluate, select best."""
        # Generate 3 candidate approaches
        generate_prompt = (
            f"Problem: {state['problem']}\n\n"
            "Generate 3 DIFFERENT solution approaches (each using a different method or assumption). "
            "Label them APPROACH A, APPROACH B, APPROACH C. "
            "Give each approach 2-3 sentences of reasoning."
        )
        candidates_raw = self.llm.simple_prompt(generate_prompt, model=MODEL_LARGE, max_tokens=500)

        # Parse candidates
        candidates = []
        for label in ["APPROACH A", "APPROACH B", "APPROACH C"]:
            match = re.search(rf"{label}:(.+?)(?=APPROACH [A-Z]:|$)", candidates_raw, re.DOTALL | re.IGNORECASE)
            if match:
                candidates.append(match.group(1).strip())
        if not candidates:
            candidates = [candidates_raw]

        # Evaluate and select best
        eval_prompt = (
            f"Problem: {state['problem']}\n\n"
            f"Here are {len(candidates)} solution approaches:\n\n"
            + "\n\n".join(f"APPROACH {i+1}:\n{c}" for i, c in enumerate(candidates))
            + "\n\nWhich approach is MOST CORRECT and EFFICIENT? "
            "Evaluate each briefly, then provide the complete correct solution as FINAL_ANSWER: [answer]"
        )
        evaluation = self.llm.simple_prompt(eval_prompt, model=MODEL_LARGE, max_tokens=500)

        match = re.search(r"FINAL_ANSWER:\s*(.+?)(?:\n\n|$)", evaluation, re.IGNORECASE | re.DOTALL)
        best_answer = match.group(1).strip() if match else candidates[0]

        return {
            "tot_candidates": candidates,
            "tot_trace": evaluation,
            "tot_answer": best_answer,
            "technique_results": {**state["technique_results"], "tree_of_thoughts": best_answer[:200]},
        }

    def _self_consistency(self, state: ReasoningState) -> dict:
        """Self-Consistency: sample 3 independent solutions, extract majority answer."""
        samples: List[str] = []
        for i in range(3):
            prompt = (
                f"Solve this problem independently (attempt {i+1}):\n\n"
                f"{state['problem']}\n\n"
                "Think step by step, then give ONLY the final numerical answer on the last line "
                "prefixed with 'ANSWER:'"
            )
            sample = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=300)
            samples.append(sample)

        # Extract answers from each sample
        extracted: List[str] = []
        for s in samples:
            match = re.search(r"ANSWER:\s*(.+?)(?:\n|$)", s, re.IGNORECASE)
            extracted.append(match.group(1).strip() if match else s.split("\n")[-1].strip())

        # Simple majority: find most common numeric value
        from collections import Counter
        # Normalise answers for comparison
        normalised = [re.sub(r"[^\d.,]", " ", a).strip() for a in extracted]
        counts = Counter(normalised)
        best, _ = counts.most_common(1)[0] if counts else ("unknown", 0)

        # Map back to original
        sc_answer = extracted[normalised.index(best)] if best in normalised else extracted[0]

        return {
            "sc_samples": extracted,
            "sc_answer": sc_answer,
            "technique_results": {**state["technique_results"], "self_consistency": sc_answer},
        }

    def _least_to_most(self, state: ReasoningState) -> dict:
        """Least-to-Most: decompose into ordered sub-problems, solve each in sequence."""
        decompose_prompt = (
            f"Decompose the following problem into a sequence of simpler sub-problems. "
            f"Each sub-problem should be solvable independently.\n\n"
            f"Problem: {state['problem']}\n\n"
            "List the sub-problems as a numbered list, from simplest to most complex."
        )
        decomposition = self.llm.simple_prompt(decompose_prompt, model=MODEL_LARGE, max_tokens=300)

        # Parse sub-problems
        subproblems = [
            line.lstrip("0123456789.) ").strip()
            for line in decomposition.split("\n")
            if re.match(r"^\d+", line.strip())
        ][:4]  # cap at 4

        if not subproblems:
            subproblems = [state["problem"]]

        # Solve sub-problems sequentially, carrying context forward
        context = ""
        for i, subp in enumerate(subproblems):
            prior_section = ("Prior solutions:\n" + context + "\n") if context else ""
            solve_prompt = (
                f"{prior_section}"
                f"Now solve this sub-problem:\n{subp}\n\n"
                "Provide a concise, direct answer."
            )
            solution = self.llm.simple_prompt(solve_prompt, model=MODEL_LARGE, max_tokens=200)
            context += f"Sub-problem {i+1}: {subp}\nSolution: {solution}\n\n"

        # Synthesise final answer
        synthesis_prompt = (
            f"Using these sub-problem solutions:\n{context}\n"
            f"Provide the final answer to: {state['problem']}"
        )
        final = self.llm.simple_prompt(synthesis_prompt, model=MODEL_LARGE, max_tokens=200)

        return {
            "ltm_subproblems": subproblems,
            "ltm_answer": final,
            "technique_results": {**state["technique_results"], "least_to_most": final[:200]},
        }

    def _compare_techniques(self, state: ReasoningState) -> dict:
        results = state["technique_results"]
        prompt = (
            f"Problem: {state['problem']}\n\n"
            "Four reasoning techniques produced these answers:\n"
            + "\n".join(f"- {k.replace('_', ' ').title()}: {v}" for k, v in results.items())
            + "\n\nBriefly compare the techniques (which was most accurate? most efficient? "
            "when would each be preferred?). Then state the DEFINITIVE_ANSWER: [answer]"
        )
        comparison = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=400)

        match = re.search(r"DEFINITIVE_ANSWER:\s*(.+?)(?:\n\n|$)", comparison, re.IGNORECASE | re.DOTALL)
        final_ans = match.group(1).strip() if match else state["cot_answer"]

        return {
            "comparison": comparison,
            "final_answer": final_ans,
        }

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(ReasoningState)

        graph.add_node("cot_reasoning", self._cot_reasoning)
        graph.add_node("tot_reasoning", self._tot_reasoning)
        graph.add_node("self_consistency", self._self_consistency)
        graph.add_node("least_to_most", self._least_to_most)
        graph.add_node("compare_techniques", self._compare_techniques)

        graph.add_edge(START, "cot_reasoning")
        graph.add_edge("cot_reasoning", "tot_reasoning")
        graph.add_edge("tot_reasoning", "self_consistency")
        graph.add_edge("self_consistency", "least_to_most")
        graph.add_edge("least_to_most", "compare_techniques")
        graph.add_edge("compare_techniques", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        problem = input_data or DEMO_PROBLEM
        try:
            app = self.build_graph()
            initial: ReasoningState = {
                "problem": problem,
                "cot_answer": "",
                "cot_trace": "",
                "tot_candidates": [],
                "tot_answer": "",
                "tot_trace": "",
                "sc_samples": [],
                "sc_answer": "",
                "ltm_subproblems": [],
                "ltm_answer": "",
                "technique_results": {},
                "comparison": "",
                "final_answer": "",
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=problem,
                output_data=final["final_answer"],
                elapsed_ms=elapsed_ms,
                steps=[
                    {"technique": k, "answer": v[:150]}
                    for k, v in final["technique_results"].items()
                ],
                metadata={
                    "technique_results": final["technique_results"],
                    "comparison_summary": final["comparison"][:300],
                    "sc_samples": final["sc_samples"],
                    "ltm_subproblems": final["ltm_subproblems"],
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=problem,
                output_data=None,
                error=traceback.format_exc(),
            )
