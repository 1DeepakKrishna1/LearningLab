"""
Pattern 13 – Human-in-the-Loop (HITL)
========================================
High-stakes agentic tasks require human oversight at critical decision
points.  This pattern inserts explicit checkpoints where the agent
pauses, presents its proposed action and reasoning to a human, and
waits for approval before proceeding.

Checkpoint types demonstrated:
  • APPROVE / REJECT   – binary gate; rejection cancels the workflow
  • MODIFY             – human can edit the agent's proposed output
  • INFORM             – non-blocking notification (always continues)

The pattern is useful for:
  – Content publication pipelines (review before publish)
  – Financial transaction approval
  – Code deployment gates
  – Medical / legal recommendation review

Demo workflow: AI-assisted blog post pipeline
  Step 1 → Generate outline      → APPROVE/MODIFY checkpoint
  Step 2 → Write full draft      → APPROVE/REJECT  checkpoint
  Step 3 → Generate social posts → INFORM          checkpoint
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from llm_client import GroqClient
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Checkpoint models
# ---------------------------------------------------------------------------


class CheckpointType(str, Enum):
    APPROVE_REJECT = "approve_reject"  # blocks until approved or rejected
    APPROVE_MODIFY = "approve_modify"  # human can approve as-is or edit
    INFORM = "inform"                  # non-blocking; just shows the output


class CheckpointDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    AUTO_APPROVED = "auto_approved"   # used in non-interactive / test mode


@dataclass
class Checkpoint:
    id: str
    checkpoint_type: CheckpointType
    description: str
    content: str                               # agent's proposed content
    decision: Optional[CheckpointDecision] = None
    modified_content: Optional[str] = None    # set if human chose MODIFY
    human_note: str = ""

    @property
    def effective_content(self) -> str:
        """Return the final content after any human modification."""
        return self.modified_content or self.content


# ---------------------------------------------------------------------------
# HITL controller
# ---------------------------------------------------------------------------


class HITLController:
    """
    Manages human checkpoints in an agentic workflow.

    In interactive mode the controller presents each checkpoint to
    the terminal and waits for keyboard input.  In non-interactive
    (automated / test) mode it auto-approves all checkpoints.
    """

    def __init__(self, interactive: bool = True, auto_approve: bool = False) -> None:
        self.interactive = interactive and sys.stdin.isatty() and not auto_approve
        self.auto_approve = auto_approve or not sys.stdin.isatty()
        self.checkpoint_log: list[Checkpoint] = []

    async def checkpoint(
        self,
        checkpoint_id: str,
        checkpoint_type: CheckpointType,
        description: str,
        content: str,
    ) -> Checkpoint:
        """
        Present a checkpoint and collect the human decision.

        Returns the ``Checkpoint`` with decision and effective content set.
        """
        cp = Checkpoint(
            id=checkpoint_id,
            checkpoint_type=checkpoint_type,
            description=description,
            content=content,
        )

        if self.auto_approve or checkpoint_type == CheckpointType.INFORM:
            cp.decision = CheckpointDecision.AUTO_APPROVED
            self.checkpoint_log.append(cp)
            return cp

        # Interactive path
        print(f"\n{'━' * 60}")
        print(f"  ⏸  CHECKPOINT: {description}")
        print(f"{'━' * 60}")
        print(content)
        print(f"{'━' * 60}")

        if checkpoint_type == CheckpointType.APPROVE_REJECT:
            decision = await self._ask_approve_reject()
            cp.decision = decision

        elif checkpoint_type == CheckpointType.APPROVE_MODIFY:
            decision, modified = await self._ask_approve_modify(content)
            cp.decision = decision
            if modified:
                cp.modified_content = modified

        self.checkpoint_log.append(cp)
        return cp

    async def _ask_approve_reject(self) -> CheckpointDecision:
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None, lambda: input("  [A]pprove / [R]eject  → ").strip().lower()
        )
        return CheckpointDecision.REJECTED if raw.startswith("r") else CheckpointDecision.APPROVED

    async def _ask_approve_modify(
        self, current: str
    ) -> tuple[CheckpointDecision, Optional[str]]:
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(
            None,
            lambda: input("  [A]pprove / [M]odify / [R]eject  → ").strip().lower(),
        )
        if raw.startswith("r"):
            return CheckpointDecision.REJECTED, None
        if raw.startswith("m"):
            print("  Enter replacement content (end with a line containing only '###'):")
            lines: list[str] = []
            while True:
                line = await loop.run_in_executor(None, input, "  > ")
                if line.strip() == "###":
                    break
                lines.append(line)
            modified = "\n".join(lines)
            return CheckpointDecision.MODIFIED, modified
        return CheckpointDecision.APPROVED, None

    @property
    def any_rejected(self) -> bool:
        return any(cp.decision == CheckpointDecision.REJECTED for cp in self.checkpoint_log)

    def summary(self) -> str:
        if not self.checkpoint_log:
            return "No checkpoints recorded."
        lines = []
        for cp in self.checkpoint_log:
            lines.append(f"  [{cp.id}] {cp.decision.value:15} {cp.description}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class HumanInTheLoopPattern(BasePattern):
    """
    Demonstrates Human-in-the-Loop workflow control.

    The agent generates content at each pipeline stage and pauses
    at defined checkpoints for human review.  In demo mode all
    checkpoints are auto-approved to allow unattended execution;
    set ``interactive=True`` for real human review.
    """

    name = "13 · Human-in-the-Loop"

    async def run(  # type: ignore[override]
        self,
        topic: str = "Best practices for securing REST APIs",
        interactive: bool = False,  # set True for live human review
    ) -> dict[str, Any]:
        self.print_header()
        print(f"Topic: {topic}")
        mode = "INTERACTIVE" if interactive else "AUTO-APPROVE (demo mode)"
        print(f"Mode:  {mode}\n")

        hitl = HITLController(interactive=interactive, auto_approve=not interactive)
        pipeline_outputs: dict[str, str] = {}

        # ── Stage 1: Generate outline ─────────────────────────────────
        outline = await self.client.complete_text(
            f"Create a 5-point outline for a technical blog post about: {topic}",
            system="You are a technical writer. Return only the outline.",
            max_tokens=250,
        )
        self.print_step("Stage 1 › Generated Outline", outline)

        cp1 = await hitl.checkpoint(
            checkpoint_id="outline_review",
            checkpoint_type=CheckpointType.APPROVE_MODIFY,
            description="Review article outline before writing full draft",
            content=outline,
        )
        self.print_step(
            "Checkpoint 1 › Decision",
            f"Decision: {cp1.decision.value}"
            + (f"\nModified content applied." if cp1.decision == CheckpointDecision.MODIFIED else ""),
        )

        if cp1.decision == CheckpointDecision.REJECTED:
            self.print_result("Pipeline halted at Stage 1 by human rejection.")
            return {"status": "rejected", "stage": "outline", "checkpoints": hitl.summary()}

        pipeline_outputs["outline"] = cp1.effective_content

        # ── Stage 2: Write full draft ─────────────────────────────────
        draft = await self.client.complete_text(
            f"Write a 350-word technical blog post using this outline:\n\n{pipeline_outputs['outline']}",
            system="You are a technical writer. Write for software developers.",
            max_tokens=700,
        )
        self.print_step("Stage 2 › Generated Draft", draft)

        cp2 = await hitl.checkpoint(
            checkpoint_id="draft_review",
            checkpoint_type=CheckpointType.APPROVE_REJECT,
            description="Approve final draft before publishing",
            content=draft,
        )
        self.print_step("Checkpoint 2 › Decision", f"Decision: {cp2.decision.value}")

        if cp2.decision == CheckpointDecision.REJECTED:
            self.print_result("Pipeline halted at Stage 2 by human rejection.")
            return {"status": "rejected", "stage": "draft", "checkpoints": hitl.summary()}

        pipeline_outputs["draft"] = cp2.effective_content

        # ── Stage 3: Social media posts (inform-only) ─────────────────
        social_posts = await self.client.complete_text(
            f"Write 2 social media posts (Twitter/LinkedIn) to promote this article:\n\n{pipeline_outputs['draft'][:300]}",
            system="You are a social media manager. Keep posts concise and engaging.",
            max_tokens=200,
        )
        self.print_step("Stage 3 › Social Media Posts", social_posts)

        await hitl.checkpoint(
            checkpoint_id="social_posts_inform",
            checkpoint_type=CheckpointType.INFORM,
            description="Social media posts generated (informational — no action required)",
            content=social_posts,
        )
        pipeline_outputs["social_posts"] = social_posts

        # ── Final report ──────────────────────────────────────────────
        self.print_step("HITL Checkpoint Summary", hitl.summary())
        self.print_result(
            f"Pipeline completed successfully.\n"
            f"Checkpoints: {len(hitl.checkpoint_log)}  |  "
            f"Rejected: {sum(1 for cp in hitl.checkpoint_log if cp.decision == CheckpointDecision.REJECTED)}"
        )

        return {
            "status": "completed",
            "topic": topic,
            "outputs": list(pipeline_outputs.keys()),
            "checkpoints": hitl.summary(),
            "draft_preview": pipeline_outputs["draft"][:200] + "…",
        }
