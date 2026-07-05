"""
Pattern 21 – Exploration and Discovery
=========================================
An autonomous exploration agent starts with a seed concept and
progressively expands a knowledge graph by:

  1. Generating questions it does not yet know the answer to.
  2. Answering those questions using the LLM.
  3. Extracting new concepts mentioned in each answer.
  4. Repeating from step 1 for newly discovered concepts.
  5. Detecting convergence when no significantly new knowledge appears.

The result is a structured knowledge graph where nodes are concepts
and edges are labelled relationships discovered during exploration.

Exploration strategies:
  BFS  – Breadth-first: fully explore one depth level before going deeper.
  DFS  – Depth-first: follow the most interesting thread as far as possible.
  Best-First – prioritise concepts scored by novelty / importance.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from llm_client import GroqClient, FAST_MODEL
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Knowledge graph types
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeNode:
    """A concept in the knowledge graph."""

    concept: str
    summary: str = ""
    depth: int = 0
    novelty_score: float = 1.0   # decreases as concept becomes "known"
    visit_count: int = 0
    source_concepts: list[str] = field(default_factory=list)  # how we discovered this


@dataclass
class KnowledgeEdge:
    """A directed relationship between two concepts."""

    source: str
    target: str
    relationship: str   # e.g. "uses", "is_a", "enables", "requires"


class KnowledgeGraph:
    """Simple in-memory directed knowledge graph."""

    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: list[KnowledgeEdge] = []

    def add_node(self, concept: str, **kwargs: Any) -> KnowledgeNode:
        if concept not in self._nodes:
            self._nodes[concept] = KnowledgeNode(concept=concept, **kwargs)
        return self._nodes[concept]

    def add_edge(self, source: str, target: str, relationship: str) -> None:
        # Avoid duplicate edges
        for e in self._edges:
            if e.source == source and e.target == target and e.relationship == relationship:
                return
        self._edges.append(KnowledgeEdge(source=source, target=target, relationship=relationship))

    def get_node(self, concept: str) -> Optional[KnowledgeNode]:
        return self._nodes.get(concept)

    def has_node(self, concept: str) -> bool:
        return concept.lower() in {k.lower() for k in self._nodes}

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def to_summary(self) -> str:
        lines = [f"Knowledge Graph: {self.node_count} concepts, {self.edge_count} relationships\n"]
        for node in sorted(self._nodes.values(), key=lambda n: n.depth):
            lines.append(
                f"  [D{node.depth}] {node.concept:<30}  "
                f"visits={node.visit_count}  "
                f"novelty={node.novelty_score:.2f}"
            )
            if node.summary:
                lines.append(f"       {node.summary[:80]}…" if len(node.summary) > 80 else f"       {node.summary}")
        return "\n".join(lines)

    def to_edge_summary(self) -> str:
        if not self._edges:
            return "No edges."
        return "\n".join(
            f"  {e.source} ──[{e.relationship}]──▶ {e.target}"
            for e in self._edges[:20]   # cap display
        ) + (f"\n  … and {len(self._edges) - 20} more" if len(self._edges) > 20 else "")


# ---------------------------------------------------------------------------
# Exploration prompts
# ---------------------------------------------------------------------------

_QUESTION_GEN_SYSTEM = """\
You are a curious researcher. Given a concept and its current known summary,
generate exactly 3 specific, distinct questions that would deepen understanding.
Return as a JSON array of strings:
["question 1", "question 2", "question 3"]
Return only valid JSON.
"""

_ANSWER_SYSTEM = """\
You are a knowledgeable expert. Answer the question concisely (100–150 words).
Focus on facts, mechanisms, and relationships to other concepts.
"""

_CONCEPT_EXTRACTOR_SYSTEM = """\
Extract all distinct technical concepts mentioned in the text.
Return as a JSON object:
{
  "concepts": ["concept1", "concept2", ...],
  "relationships": [
    {"source": "A", "target": "B", "relationship": "verb phrase"}
  ]
}
Return only valid JSON. Limit to 5 concepts and 4 relationships max.
"""

_NOVELTY_SYSTEM = """\
Rate how novel this concept is relative to the seed topic (0.0–1.0).
1.0 = completely new territory; 0.0 = already well covered.
Return a single float only.
"""


# ---------------------------------------------------------------------------
# Exploration strategies
# ---------------------------------------------------------------------------

class ExplorationStrategy(str, Enum):
    BFS        = "bfs"
    DFS        = "dfs"
    BEST_FIRST = "best_first"


# ---------------------------------------------------------------------------
# Explorer agent
# ---------------------------------------------------------------------------


class ExplorationAgent:
    """
    Autonomous knowledge graph builder.

    Starts from a seed concept and expands the graph iteratively
    using the selected exploration strategy.
    """

    def __init__(
        self,
        client: GroqClient,
        *,
        strategy: ExplorationStrategy = ExplorationStrategy.BFS,
        max_depth: int = 3,
        max_nodes: int = 15,
        convergence_threshold: float = 0.15,
    ) -> None:
        self.client = client
        self.strategy = strategy
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.convergence_threshold = convergence_threshold
        self.graph = KnowledgeGraph()
        self._exploration_log: list[str] = []

    async def _generate_questions(self, node: KnowledgeNode) -> list[str]:
        raw = await self.client.complete_text(
            f"Concept: {node.concept}\nKnown: {node.summary or 'Unknown'}",
            system=_QUESTION_GEN_SYSTEM,
            model=FAST_MODEL,
            temperature=0.6,
            max_tokens=200,
        )
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        try:
            questions = json.loads(clean)
            return questions[:3] if isinstance(questions, list) else []
        except json.JSONDecodeError:
            return [f"What is {node.concept}?"]

    async def _answer_question(self, question: str) -> str:
        return await self.client.complete_text(
            question, system=_ANSWER_SYSTEM, max_tokens=250
        )

    async def _extract_concepts(self, text: str, source_concept: str) -> tuple[list[str], list[dict]]:
        raw = await self.client.complete_text(
            text[:800],
            system=_CONCEPT_EXTRACTOR_SYSTEM,
            model=FAST_MODEL,
            temperature=0.2,
            max_tokens=250,
        )
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        try:
            data = json.loads(clean)
            concepts = [c for c in data.get("concepts", []) if isinstance(c, str)][:5]
            relationships = data.get("relationships", [])[:4]
            return concepts, relationships
        except json.JSONDecodeError:
            return [], []

    async def _score_novelty(self, concept: str) -> float:
        raw = await self.client.complete_text(
            f"Known concepts: {list(self.graph._nodes.keys())[:10]}\nNew concept: {concept}",
            system=_NOVELTY_SYSTEM,
            model=FAST_MODEL,
            temperature=0.0,
            max_tokens=10,
        )
        try:
            return min(1.0, max(0.0, float(raw.strip())))
        except ValueError:
            return 0.5

    def _get_frontier(self, current_frontier: list[KnowledgeNode]) -> list[KnowledgeNode]:
        """Order the frontier based on the exploration strategy."""
        if self.strategy == ExplorationStrategy.BFS:
            return current_frontier   # already in order
        if self.strategy == ExplorationStrategy.DFS:
            return list(reversed(current_frontier))
        # BEST_FIRST: highest novelty first
        return sorted(current_frontier, key=lambda n: n.novelty_score, reverse=True)

    async def explore(self, seed_concept: str) -> KnowledgeGraph:
        """
        Run the full exploration loop from the seed concept.

        Returns the populated KnowledgeGraph.
        """
        # Bootstrap seed node
        seed = self.graph.add_node(seed_concept, depth=0, novelty_score=1.0)
        seed.summary = f"Seed concept: {seed_concept}"

        frontier: deque[KnowledgeNode] = deque([seed])
        visited: set[str] = {seed_concept.lower()}
        new_nodes_this_round = 1

        while frontier and self.graph.node_count < self.max_nodes:
            node = frontier.popleft()

            if node.depth >= self.max_depth:
                continue

            node.visit_count += 1
            logger.debug("Exploring: %s (depth=%d)", node.concept, node.depth)
            self._exploration_log.append(f"Visiting: {node.concept} (D{node.depth})")

            # Generate questions about this node
            questions = await self._generate_questions(node)

            for question in questions:
                if self.graph.node_count >= self.max_nodes:
                    break

                # Answer the question
                answer = await self._answer_question(question)

                # Update node summary if empty
                if not node.summary or len(node.summary) < 50:
                    node.summary = answer[:200]

                # Extract new concepts and relationships
                new_concepts, relationships = await self._extract_concepts(answer, node.concept)

                # Add relationships to graph
                for rel in relationships:
                    src = rel.get("source", "")
                    tgt = rel.get("target", "")
                    rel_type = rel.get("relationship", "relates_to")
                    if src and tgt:
                        self.graph.add_node(src)
                        self.graph.add_node(tgt)
                        self.graph.add_edge(src, tgt, rel_type)

                # Add new concepts to graph and frontier
                for concept in new_concepts:
                    if concept.lower() not in visited and self.graph.node_count < self.max_nodes:
                        visited.add(concept.lower())
                        novelty = await self._score_novelty(concept)

                        # Convergence check
                        if novelty < self.convergence_threshold:
                            logger.debug("Converged on %s (novelty=%.2f)", concept, novelty)
                            continue

                        new_node = self.graph.add_node(
                            concept,
                            depth=node.depth + 1,
                            novelty_score=novelty,
                            source_concepts=[node.concept],
                        )
                        self.graph.add_edge(node.concept, concept, "leads_to")
                        frontier.append(new_node)
                        new_nodes_this_round += 1

        return self.graph


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class ExplorationDiscoveryPattern(BasePattern):
    """
    Demonstrates autonomous knowledge graph exploration.

    The agent starts from a seed topic and expands outward, discovering
    related concepts, building a graph of relationships, and detecting
    convergence when the knowledge frontier stabilises.
    """

    name = "21 · Exploration and Discovery"

    async def run(  # type: ignore[override]
        self,
        seed: str = "Zero-Knowledge Proofs",
        strategy: str = "bfs",
        max_depth: int = 2,
        max_nodes: int = 12,
    ) -> dict[str, Any]:
        self.print_header()
        print(f"Seed concept : {seed}")
        print(f"Strategy     : {strategy.upper()}")
        print(f"Max depth    : {max_depth}  |  Max nodes: {max_nodes}\n")

        strat = ExplorationStrategy(strategy.lower())
        agent = ExplorationAgent(
            self.client,
            strategy=strat,
            max_depth=max_depth,
            max_nodes=max_nodes,
            convergence_threshold=0.12,
        )

        self.print_step("Exploration Start", f"Seeding with: '{seed}'")
        graph = await agent.explore(seed)

        # Display exploration log
        self.print_step(
            "Exploration Log",
            "\n".join(f"  {entry}" for entry in agent._exploration_log[:20]),
        )

        # Display graph
        self.print_step("Knowledge Graph — Nodes", graph.to_summary())
        self.print_step("Knowledge Graph — Edges", graph.to_edge_summary())

        # Discovery insights: ask LLM to synthesise the graph
        graph_text = "\n".join(
            f"- {n.concept}: {n.summary[:100]}"
            for n in list(graph._nodes.values())[:10]
        )
        insights = await self.client.complete_text(
            f"Based on exploring '{seed}', these concepts were discovered:\n\n{graph_text}\n\n"
            f"What are the 3 most important insights from this knowledge map?",
            system="You are an expert knowledge synthesiser. Be insightful and concise.",
            max_tokens=300,
        )
        self.print_step("Discovery Insights", insights)

        self.print_result(
            f"Discovered {graph.node_count} concepts and {graph.edge_count} relationships "
            f"from seed: '{seed}'"
        )

        return {
            "seed": seed,
            "strategy": strategy,
            "nodes_discovered": graph.node_count,
            "edges_discovered": graph.edge_count,
            "concepts": list(graph._nodes.keys()),
            "insights": insights,
        }
