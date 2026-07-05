"""
Pattern 11 – Goal Setting and Monitoring
==========================================
The agent operates around an explicit, structured goal hierarchy.
It decomposes a high-level objective into SMART milestones, executes
work toward each milestone, and continuously monitors / reports
progress using a structured GoalTracker.

Goal lifecycle in this demo:
  1. Set:      define a high-level goal and decompose it into milestones
  2. Execute:  work toward each milestone, producing artefacts
  3. Assess:   evaluate milestone completion (LLM-judged 0–100%)
  4. Monitor:  generate a progress report and flag any blockers
  5. Conclude: mark goal as achieved or escalate blockers
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from llm_client import GroqClient, FAST_MODEL
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Goal data model
# ---------------------------------------------------------------------------


class MilestoneStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"


@dataclass
class Milestone:
    id: int
    description: str
    success_criteria: str
    status: MilestoneStatus = MilestoneStatus.PENDING
    progress_pct: int = 0          # 0 – 100
    output: str = ""
    blocker: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Goal:
    title: str
    description: str
    milestones: list[Milestone] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def overall_progress(self) -> int:
        if not self.milestones:
            return 0
        return round(sum(m.progress_pct for m in self.milestones) / len(self.milestones))

    @property
    def is_achieved(self) -> bool:
        return all(m.status == MilestoneStatus.COMPLETE for m in self.milestones)

    @property
    def has_blockers(self) -> bool:
        return any(m.status == MilestoneStatus.BLOCKED for m in self.milestones)

    def status_table(self) -> str:
        lines = [f"Goal: {self.title}  (overall {self.overall_progress}%)\n"]
        for m in self.milestones:
            blocker_tag = f"  ⚠ {m.blocker}" if m.blocker else ""
            lines.append(
                f"  M{m.id} [{m.status.value:11}] {m.progress_pct:3}%  {m.description}{blocker_tag}"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_DECOMPOSE_SYSTEM = """\
You are a project manager. Given a goal, decompose it into 3–4 concrete,
measurable milestones. Each milestone must have a clear success criterion.

Respond with a JSON array:
[
  {"description": "...", "success_criteria": "..."},
  ...
]
Return only valid JSON (no markdown fences).
"""

_EXECUTOR_SYSTEM = """\
You are a diligent executor. Carry out the specified milestone thoroughly.
Produce a concrete artefact (plan, draft, analysis, etc.) as the output.
Be specific and actionable (150–200 words).
"""

_ASSESSOR_SYSTEM = """\
You are an objective milestone assessor. Given a milestone's description,
success criteria, and the work output, score completion as a percentage (0–100)
and identify any blockers.

Respond with JSON only:
{"progress_pct": <int 0-100>, "status": "complete"|"in_progress"|"blocked", "blocker": "<string or null>"}
"""

_MONITOR_SYSTEM = """\
You are a progress monitor and project status reporter.
Given a goal and the current milestone statuses, write a concise (150 words)
progress report covering: achievements, current status, risks, and next steps.
"""


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class GoalMonitoringPattern(BasePattern):
    """
    Demonstrates structured goal setting, execution, and monitoring.

    Phase 1 – Set:     decompose goal into SMART milestones.
    Phase 2 – Execute: produce output for each milestone.
    Phase 3 – Assess:  score each milestone's completion.
    Phase 4 – Report:  generate a structured progress report.
    """

    name = "11 · Goal Setting and Monitoring"

    async def _decompose_goal(self, goal: Goal) -> list[Milestone]:
        raw = await self.client.complete_text(
            f"Goal title: {goal.title}\nDescription: {goal.description}",
            system=_DECOMPOSE_SYSTEM,
            temperature=0.3,
            max_tokens=400,
        )
        # Strip markdown fences
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        try:
            items = json.loads(clean)
            return [
                Milestone(
                    id=i + 1,
                    description=item["description"],
                    success_criteria=item["success_criteria"],
                )
                for i, item in enumerate(items)
            ]
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Milestone parse failed: %s — using fallback", exc)
            # Fallback: parse numbered lines
            lines = [l.strip() for l in raw.splitlines() if l.strip() and l[0].isdigit()]
            return [
                Milestone(id=i + 1, description=l, success_criteria="Produce concrete output")
                for i, l in enumerate(lines[:4])
            ]

    async def _execute_milestone(self, goal: Goal, milestone: Milestone) -> str:
        return await self.client.complete_text(
            f"Goal: {goal.title}\n"
            f"Milestone {milestone.id}: {milestone.description}\n"
            f"Success criteria: {milestone.success_criteria}\n\n"
            f"Carry out this milestone now:",
            system=_EXECUTOR_SYSTEM,
            max_tokens=400,
        )

    async def _assess_milestone(self, milestone: Milestone) -> dict[str, Any]:
        raw = await self.client.complete_text(
            json.dumps({
                "description": milestone.description,
                "success_criteria": milestone.success_criteria,
                "output": milestone.output[:800],  # truncate for token economy
            }),
            system=_ASSESSOR_SYSTEM,
            model=FAST_MODEL,
            temperature=0.0,
            max_tokens=150,
        )
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            return {"progress_pct": 75, "status": "in_progress", "blocker": None}

    async def _generate_report(self, goal: Goal) -> str:
        return await self.client.complete_text(
            goal.status_table(),
            system=_MONITOR_SYSTEM,
            max_tokens=400,
        )

    async def run(  # type: ignore[override]
        self,
        goal_title: str = "Launch an open-source Python library for LLM prompt management",
        goal_description: str = (
            "Build and release a well-documented, production-ready Python library that helps "
            "developers manage, version, and test LLM prompts across multiple providers."
        ),
    ) -> dict[str, Any]:
        self.print_header()
        print(f"Goal: {goal_title}\n")

        goal = Goal(title=goal_title, description=goal_description)

        # ── Phase 1: Decompose ────────────────────────────────────────
        goal.milestones = await self._decompose_goal(goal)
        self.print_step(
            "Phase 1 › Goal Decomposition",
            "\n".join(
                f"  M{m.id}: {m.description}\n       Criteria: {m.success_criteria}"
                for m in goal.milestones
            ),
        )

        # ── Phase 2 & 3: Execute and Assess each milestone ───────────
        for m in goal.milestones:
            m.status = MilestoneStatus.IN_PROGRESS

            # Execute
            m.output = await self._execute_milestone(goal, m)
            self.print_step(f"Phase 2 › Execute M{m.id}: {m.description}", m.output)

            # Assess
            assessment = await self._assess_milestone(m)
            m.progress_pct = min(100, max(0, int(assessment.get("progress_pct", 75))))
            raw_status = assessment.get("status", "in_progress")
            try:
                m.status = MilestoneStatus(raw_status)
            except ValueError:
                m.status = MilestoneStatus.IN_PROGRESS
            m.blocker = assessment.get("blocker")
            if m.status == MilestoneStatus.COMPLETE:
                m.completed_at = datetime.now(timezone.utc).isoformat()

            self.print_step(
                f"Phase 3 › Assess M{m.id}",
                f"Progress: {m.progress_pct}%  |  Status: {m.status.value}"
                + (f"  |  Blocker: {m.blocker}" if m.blocker else ""),
            )

        # ── Phase 4: Monitor & Report ─────────────────────────────────
        self.print_step("Phase 4 › Goal Status Dashboard", goal.status_table())
        report = await self._generate_report(goal)
        self.print_step("Phase 4 › Progress Report", report)

        conclusion = "ACHIEVED" if goal.is_achieved else ("BLOCKED" if goal.has_blockers else "IN PROGRESS")
        self.print_result(
            f"Goal status: {conclusion}  |  Overall progress: {goal.overall_progress}%"
        )

        return {
            "goal": goal_title,
            "overall_progress": goal.overall_progress,
            "status": conclusion,
            "milestones": [
                {
                    "id": m.id,
                    "description": m.description,
                    "progress_pct": m.progress_pct,
                    "status": m.status.value,
                }
                for m in goal.milestones
            ],
            "report": report,
        }
