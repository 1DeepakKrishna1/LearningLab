"""
Pattern 21: Exploration and Discovery
=======================================
Concept: Agent explores an unknown solution space using beam search over
LLM-generated hypotheses. At each depth level, it generates candidate ideas,
scores them, prunes to the top-k (beam), and expands the survivors. Novel
combinations are discovered through cross-pollination between beam elements.

Search strategy:
  - Beam width: k=3 (keep top 3 hypotheses per depth level)
  - Max depth: 3 expansion rounds
  - Scoring: novelty × feasibility × impact (each 1-5)

Graph:  START → initialise_search → generate_hypotheses → score_hypotheses
              → prune_beam
                  |
            [depth < max] → expand_promising → generate_hypotheses (loop)
                  |
            [depth >= max] → synthesise_discoveries → END

Demo:   "Discover innovative product ideas combining AI with sustainability"
"""
from __future__ import annotations

import json
import re
import traceback
from typing import Annotated, Any, Dict, List
import operator

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL

BEAM_WIDTH = 3
MAX_DEPTH = 2    # keep short for demo; increase for deeper exploration
HYPOTHESES_PER_NODE = 3


class ExplorationState(TypedDict):
    exploration_goal: str
    search_directions: List[str]
    current_depth: int
    max_depth: int
    beam_width: int
    all_hypotheses: Annotated[List[Dict[str, Any]], operator.add]
    active_beam: List[Dict[str, Any]]    # top-k hypotheses being expanded
    pruned: Annotated[List[Dict[str, Any]], operator.add]
    discoveries: Annotated[List[str], operator.add]
    final_synthesis: str


class PatternExplorationDiscovery(BasePattern):
    PATTERN_NUMBER = 21
    PATTERN_NAME = "Exploration and Discovery"
    DESCRIPTION = (
        "Beam search over LLM-generated hypotheses; score, prune, expand to discover novelty."
    )

    # ------------------------------------------------------------------ nodes

    def _initialise_search(self, state: ExplorationState) -> dict:
        """Generate initial search directions from the goal."""
        prompt = (
            f"Goal: {state['exploration_goal']}\n\n"
            "Generate exactly 3 distinct high-level search directions for exploring this space. "
            "Each should represent a fundamentally different angle of attack.\n"
            "Return ONLY a JSON array of 3 strings. Example: [\"direction A\", \"direction B\", \"direction C\"]"
        )
        raw = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=200)
        directions: List[str] = []
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            try:
                directions = json.loads(match.group())
            except json.JSONDecodeError:
                pass
        if not directions:
            directions = [raw.strip()][:3]
        if len(directions) < 3:
            directions += [f"Alternative direction {i+1}" for i in range(3 - len(directions))]

        return {"search_directions": directions[:3]}

    def _generate_hypotheses(self, state: ExplorationState) -> dict:
        """Generate hypotheses by expanding from each node in the active beam
        (or from search directions on the first pass)."""
        depth = state["current_depth"]
        seeds = state["active_beam"] if state["active_beam"] else [
            {"id": f"seed_{i}", "concept": d, "score": 3.0}
            for i, d in enumerate(state["search_directions"])
        ]

        new_hypotheses: List[Dict[str, Any]] = []
        for seed in seeds:
            seed_concept = seed.get("concept", seed.get("hypothesis", str(seed)))
            prompt = (
                f"Goal: {state['exploration_goal']}\n"
                f"Starting from this concept: '{seed_concept}'\n\n"
                f"Generate {HYPOTHESES_PER_NODE} novel, specific product or solution ideas "
                f"that extend or combine with this concept. Each idea should be concrete and actionable.\n"
                f"Return ONLY a JSON array of {HYPOTHESES_PER_NODE} strings."
            )
            raw = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=400)
            ideas: List[str] = []
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            if match:
                try:
                    ideas = json.loads(match.group())
                except json.JSONDecodeError:
                    ideas = [l.strip().lstrip("\"'1234567890.-) ") for l in raw.split("\n") if l.strip()][:HYPOTHESES_PER_NODE]

            for i, idea in enumerate(ideas[:HYPOTHESES_PER_NODE]):
                new_hypotheses.append({
                    "id": f"h_d{depth}_{seed['id']}_{i}",
                    "hypothesis": str(idea).strip(),
                    "parent_id": seed["id"],
                    "depth": depth,
                    "score": 0.0,
                })

        return {
            "all_hypotheses": new_hypotheses,
            "active_beam": new_hypotheses,    # temp — will be overwritten by score + prune
        }

    def _score_hypotheses(self, state: ExplorationState) -> dict:
        """Score each hypothesis on novelty, feasibility, and impact."""
        candidates = state["active_beam"]
        if not candidates:
            return {}

        # Batch evaluation for efficiency
        hypothesis_list = "\n".join(
            f"{i+1}. {h['hypothesis']}" for i, h in enumerate(candidates)
        )
        prompt = (
            f"Goal: {state['exploration_goal']}\n\n"
            f"Score each of these {len(candidates)} ideas on:\n"
            "- novelty (1-5): how original and unexpected\n"
            "- feasibility (1-5): how realistic to implement\n"
            "- impact (1-5): potential positive impact\n\n"
            f"Ideas:\n{hypothesis_list}\n\n"
            f"Return ONLY a JSON array of {len(candidates)} objects with keys "
            '"novelty", "feasibility", "impact". Match order exactly.'
        )
        raw = self.llm.simple_prompt(prompt, model=MODEL_SMALL, max_tokens=400)

        scores: List[Dict] = []
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            try:
                scores = json.loads(match.group())
            except json.JSONDecodeError:
                pass

        scored = []
        for i, h in enumerate(candidates):
            if i < len(scores):
                s = scores[i]
                try:
                    n = max(1.0, min(5.0, float(s.get("novelty", 3))))
                    f_ = max(1.0, min(5.0, float(s.get("feasibility", 3))))
                    im = max(1.0, min(5.0, float(s.get("impact", 3))))
                    composite = round((n + f_ + im) / 3, 2)
                except (TypeError, ValueError):
                    n = f_ = im = 3.0
                    composite = 3.0
            else:
                n = f_ = im = 3.0
                composite = 3.0

            scored.append({
                **h,
                "novelty": n,
                "feasibility": f_,
                "impact": im,
                "score": composite,
            })

        return {"active_beam": scored}

    def _prune_beam(self, state: ExplorationState) -> dict:
        """Keep top-k hypotheses; log the pruned ones."""
        sorted_beam = sorted(state["active_beam"], key=lambda h: h["score"], reverse=True)
        top_k = sorted_beam[:state["beam_width"]]
        pruned = sorted_beam[state["beam_width"]:]

        discoveries = [h["hypothesis"] for h in top_k]

        return {
            "active_beam": top_k,
            "pruned": pruned,
            "discoveries": discoveries,
        }

    def _should_continue(self, state: ExplorationState) -> str:
        if state["current_depth"] < state["max_depth"]:
            return "expand"
        return "synthesise"

    def _expand_promising(self, state: ExplorationState) -> dict:
        return {"current_depth": state["current_depth"] + 1}

    def _synthesise_discoveries(self, state: ExplorationState) -> dict:
        top_ideas = state["active_beam"]
        all_disc = state["discoveries"]

        ideas_text = "\n".join(
            f"- (score {h['score']:.1f}) {h['hypothesis']}" for h in top_ideas
        )
        prompt = (
            f"Goal: {state['exploration_goal']}\n\n"
            f"After a beam search exploration, the top discoveries are:\n{ideas_text}\n\n"
            "Synthesise these into:\n"
            "1. The single BEST IDEA (most novel + feasible + impactful)\n"
            "2. A HYBRID concept combining the best elements of 2-3 ideas\n"
            "3. Three KEY INSIGHTS about this solution space\n\n"
            "Be concrete and actionable."
        )
        synthesis = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=600)
        return {"final_synthesis": synthesis}

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(ExplorationState)

        graph.add_node("initialise_search", self._initialise_search)
        graph.add_node("generate_hypotheses", self._generate_hypotheses)
        graph.add_node("score_hypotheses", self._score_hypotheses)
        graph.add_node("prune_beam", self._prune_beam)
        graph.add_node("expand_promising", self._expand_promising)
        graph.add_node("synthesise_discoveries", self._synthesise_discoveries)

        graph.add_edge(START, "initialise_search")
        graph.add_edge("initialise_search", "generate_hypotheses")
        graph.add_edge("generate_hypotheses", "score_hypotheses")
        graph.add_edge("score_hypotheses", "prune_beam")
        graph.add_conditional_edges(
            "prune_beam",
            self._should_continue,
            {"expand": "expand_promising", "synthesise": "synthesise_discoveries"},
        )
        graph.add_edge("expand_promising", "generate_hypotheses")
        graph.add_edge("synthesise_discoveries", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial: ExplorationState = {
                "exploration_goal": input_data,
                "search_directions": [],
                "current_depth": 0,
                "max_depth": kwargs.get("max_depth", MAX_DEPTH),
                "beam_width": kwargs.get("beam_width", BEAM_WIDTH),
                "all_hypotheses": [],
                "active_beam": [],
                "pruned": [],
                "discoveries": [],
                "final_synthesis": "",
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["final_synthesis"],
                elapsed_ms=elapsed_ms,
                steps=[
                    {"hypothesis": h["hypothesis"], "score": h["score"]}
                    for h in final["active_beam"]
                ],
                metadata={
                    "total_hypotheses_generated": len(final["all_hypotheses"]),
                    "beam_width": final["beam_width"],
                    "depth_reached": final["current_depth"],
                    "top_discoveries": [h["hypothesis"] for h in final["active_beam"][:3]],
                    "search_directions": final["search_directions"],
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
