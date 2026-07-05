"""
Pattern 7 – Multi-Agent
=========================
Multiple specialised agents, each with a distinct role and system
prompt, collaborate on a shared task.  An Orchestrator coordinates
the workflow, delegating work to the right agent at each stage and
synthesising the final output.

Agent roster in this demo:
  ┌─────────────────┐
  │   Orchestrator  │  Directs the workflow; decides agent order & inputs
  └────────┬────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
  Researcher    Writer
  (gathers    (drafts
   facts)      content)
               │
               ▼
            Reviewer
          (critique &
           final edit)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from llm_client import GroqClient, Message
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------


class AgentRole(str, Enum):
    ORCHESTRATOR = "Orchestrator"
    RESEARCHER = "Researcher"
    WRITER = "Writer"
    REVIEWER = "Reviewer"


_AGENT_SYSTEMS: dict[AgentRole, str] = {
    AgentRole.ORCHESTRATOR: (
        "You are an expert project orchestrator. Your job is to coordinate a team of "
        "specialist agents (Researcher, Writer, Reviewer) to produce high-quality content. "
        "Provide clear, specific instructions to each agent based on their role."
    ),
    AgentRole.RESEARCHER: (
        "You are a meticulous researcher. Given a topic, produce a concise research brief "
        "containing: key facts, current trends, important statistics, and notable challenges. "
        "Be factual and specific. Format with clear headings."
    ),
    AgentRole.WRITER: (
        "You are a skilled technical writer. Using the provided research brief, write a "
        "polished, engaging article (300–350 words). Include an introduction, 2–3 body "
        "paragraphs, and a conclusion. Write for a technically literate audience."
    ),
    AgentRole.REVIEWER: (
        "You are a rigorous editor and quality reviewer. Review the provided article for: "
        "accuracy, clarity, flow, grammar, and overall quality. "
        "First list specific issues found (if any), then produce a final polished version."
    ),
}


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------


@dataclass
class AgentMessage:
    """A message produced by an agent."""

    role: AgentRole
    content: str


@dataclass
class Agent:
    """A specialised LLM agent with a fixed role and system prompt."""

    role: AgentRole
    client: GroqClient

    @property
    def system(self) -> str:
        return _AGENT_SYSTEMS[self.role]

    async def run(
        self,
        user_message: str,
        history: Optional[list[AgentMessage]] = None,
        max_tokens: int = 600,
    ) -> AgentMessage:
        """
        Run the agent with an optional shared history context.

        Args:
            user_message: The specific instruction for this agent.
            history:      Prior agent outputs to include as context.
            max_tokens:   Token limit for the response.

        Returns:
            ``AgentMessage`` with this agent's role and output.
        """
        messages: list[Message] = [Message(role="system", content=self.system)]

        if history:
            context_block = "\n\n".join(
                f"[{msg.role.value} output]\n{msg.content}" for msg in history
            )
            messages.append(
                Message(
                    role="user",
                    content=f"Context from previous agents:\n\n{context_block}",
                )
            )
            messages.append(
                Message(role="assistant", content="Understood. I will use this context.")
            )

        messages.append(Message(role="user", content=user_message))

        response = await self.client.complete(messages, max_tokens=max_tokens)
        return AgentMessage(role=self.role, content=response.content)


# ---------------------------------------------------------------------------
# Multi-agent result
# ---------------------------------------------------------------------------


@dataclass
class MultiAgentResult:
    topic: str
    orchestration_plan: str = ""
    agent_outputs: list[AgentMessage] = field(default_factory=list)
    final_article: str = ""


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class MultiAgentPattern(BasePattern):
    """
    Demonstrates a coordinated multi-agent pipeline.

    The Orchestrator defines instructions for each specialist agent.
    Agents execute sequentially, each receiving prior outputs as context.
    """

    name = "7 · Multi-Agent"

    def _build_agents(self) -> dict[AgentRole, Agent]:
        return {role: Agent(role=role, client=self.client) for role in AgentRole}

    async def run(  # type: ignore[override]
        self,
        topic: str = "The future of AI-assisted software development by 2030",
    ) -> MultiAgentResult:
        self.print_header()
        print(f"Topic: {topic}\n")

        agents = self._build_agents()
        result = MultiAgentResult(topic=topic)

        # ── Step 0: Orchestrator creates the plan ─────────────────────
        orchestrator = agents[AgentRole.ORCHESTRATOR]
        plan_response = await orchestrator.run(
            user_message=(
                f"We need to produce a high-quality article about: '{topic}'.\n\n"
                f"Write brief, specific instructions for each of these agents:\n"
                f"1. Researcher – what to research and what format to use\n"
                f"2. Writer – what style/structure to write in\n"
                f"3. Reviewer – what quality criteria to focus on\n\n"
                f"Keep each instruction to 1–2 sentences."
            ),
            max_tokens=350,
        )
        result.orchestration_plan = plan_response.content
        self.print_step("Step 0 › Orchestrator Plan", plan_response.content)

        history: list[AgentMessage] = []

        # ── Step 1: Researcher ────────────────────────────────────────
        researcher = agents[AgentRole.RESEARCHER]
        research_output = await researcher.run(
            user_message=f"Research this topic thoroughly: {topic}",
            max_tokens=500,
        )
        history.append(research_output)
        self.print_step("Step 1 › Researcher Output", research_output.content)

        # ── Step 2: Writer ────────────────────────────────────────────
        writer = agents[AgentRole.WRITER]
        writer_output = await writer.run(
            user_message=(
                f"Using the research provided in the context, write a polished article "
                f"about: {topic}"
            ),
            history=history,
            max_tokens=700,
        )
        history.append(writer_output)
        self.print_step("Step 2 › Writer Output", writer_output.content)

        # ── Step 3: Reviewer ──────────────────────────────────────────
        reviewer = agents[AgentRole.REVIEWER]
        reviewer_output = await reviewer.run(
            user_message=(
                "Review the article in the context and produce the final polished version."
            ),
            history=history,
            max_tokens=700,
        )
        history.append(reviewer_output)
        result.agent_outputs = history
        result.final_article = reviewer_output.content
        self.print_step("Step 3 › Reviewer Output", reviewer_output.content)

        self.print_result(
            f"Multi-agent pipeline complete.\n"
            f"Agents involved: {', '.join(h.role.value for h in history)}\n\n"
            f"{result.final_article}"
        )
        return result
