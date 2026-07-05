"""
Pattern 20 – Prioritization
==============================
Real-world agents receive many competing requests simultaneously.
A prioritization layer decides WHAT to work on, in WHAT order,
so the most critical work is completed first even under resource constraints.

Frameworks implemented:
  1. Eisenhower Matrix    – categorise by Urgency × Importance
  2. RICE Scoring         – Reach × Impact × Confidence / Effort
  3. Priority Queue       – heap-based execution queue with dynamic
                            reprioritisation on dependency resolution
  4. LLM-assisted Triage  – use LLM to score tasks when criteria are ambiguous

Task lifecycle:
  Backlog → Scored → Queued → In-Progress → Done / Deferred
"""

from __future__ import annotations

import asyncio
import heapq
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
# Task model
# ---------------------------------------------------------------------------


class Priority(str, Enum):
    CRITICAL = "critical"   # P0
    HIGH     = "high"       # P1
    MEDIUM   = "medium"     # P2
    LOW      = "low"        # P3
    DEFERRED = "deferred"   # P4


class EisenhowerQuadrant(str, Enum):
    Q1_DO_NOW    = "Q1: Urgent + Important → Do Now"
    Q2_SCHEDULE  = "Q2: Not Urgent + Important → Schedule"
    Q3_DELEGATE  = "Q3: Urgent + Not Important → Delegate"
    Q4_ELIMINATE = "Q4: Not Urgent + Not Important → Eliminate"


_PRIORITY_SCORE: dict[Priority, int] = {
    Priority.CRITICAL: 100,
    Priority.HIGH:      75,
    Priority.MEDIUM:    50,
    Priority.LOW:       25,
    Priority.DEFERRED:   0,
}


@dataclass
class Task:
    task_id: str
    title: str
    description: str
    urgency: int         = 5    # 1–10
    importance: int      = 5    # 1–10
    reach: int           = 5    # 1–10  (RICE)
    impact: int          = 5    # 1–10  (RICE)
    confidence: int      = 7    # 1–10  (RICE, %)
    effort: int          = 5    # 1–10  (higher = more effort)
    deadline: Optional[str]  = None
    dependencies: list[str]  = field(default_factory=list)
    priority: Priority       = Priority.MEDIUM
    quadrant: Optional[EisenhowerQuadrant] = None
    rice_score: float        = 0.0
    composite_score: float   = 0.0
    status: str              = "backlog"
    result: str              = ""

    def __lt__(self, other: "Task") -> bool:
        return self.composite_score > other.composite_score  # max-heap via min-heap negation

    def assign_eisenhower(self) -> None:
        if self.urgency >= 6 and self.importance >= 6:
            self.quadrant = EisenhowerQuadrant.Q1_DO_NOW
        elif self.urgency < 6 and self.importance >= 6:
            self.quadrant = EisenhowerQuadrant.Q2_SCHEDULE
        elif self.urgency >= 6 and self.importance < 6:
            self.quadrant = EisenhowerQuadrant.Q3_DELEGATE
        else:
            self.quadrant = EisenhowerQuadrant.Q4_ELIMINATE

    def compute_rice(self) -> None:
        self.rice_score = round(
            (self.reach * self.impact * (self.confidence / 10)) / max(self.effort, 1), 2
        )

    def compute_composite(self) -> None:
        """Weighted composite: Eisenhower + RICE + priority override."""
        eisenhower_weight = {
            EisenhowerQuadrant.Q1_DO_NOW:    4.0,
            EisenhowerQuadrant.Q2_SCHEDULE:  3.0,
            EisenhowerQuadrant.Q3_DELEGATE:  2.0,
            EisenhowerQuadrant.Q4_ELIMINATE: 1.0,
            None:                            2.0,
        }[self.quadrant]
        self.composite_score = round(
            (eisenhower_weight * 15)
            + (self.rice_score * 10)
            + _PRIORITY_SCORE[self.priority] * 0.5,
            2,
        )

    def score_all(self) -> None:
        self.assign_eisenhower()
        self.compute_rice()
        self.compute_composite()


# ---------------------------------------------------------------------------
# LLM triage
# ---------------------------------------------------------------------------

_TRIAGE_SYSTEM = """\
You are a product manager performing task triage.
Given a task description, assign scores (1–10) for:
  urgency, importance, reach, impact, confidence, effort
And suggest a priority: critical | high | medium | low | deferred

Respond with JSON only:
{
  "urgency": int,
  "importance": int,
  "reach": int,
  "impact": int,
  "confidence": int,
  "effort": int,
  "priority": "critical|high|medium|low|deferred",
  "rationale": "one sentence"
}
"""


async def llm_triage_task(client: GroqClient, task: Task) -> None:
    """Use the LLM to score a task when manual scores are not provided."""
    raw = await client.complete_text(
        f"Task: {task.title}\nDescription: {task.description}",
        system=_TRIAGE_SYSTEM,
        model=FAST_MODEL,
        temperature=0.2,
        max_tokens=200,
    )
    clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    try:
        data = json.loads(clean)
        task.urgency    = min(10, max(1, int(data.get("urgency",    task.urgency))))
        task.importance = min(10, max(1, int(data.get("importance", task.importance))))
        task.reach      = min(10, max(1, int(data.get("reach",      task.reach))))
        task.impact     = min(10, max(1, int(data.get("impact",     task.impact))))
        task.confidence = min(10, max(1, int(data.get("confidence", task.confidence))))
        task.effort     = min(10, max(1, int(data.get("effort",     task.effort))))
        raw_prio = data.get("priority", "medium").lower()
        task.priority = Priority(raw_prio) if raw_prio in Priority._value2member_map_ else Priority.MEDIUM
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        logger.warning("Triage parse failed for task %s: %s", task.task_id, exc)


# ---------------------------------------------------------------------------
# Priority scheduler
# ---------------------------------------------------------------------------


class PriorityScheduler:
    """
    Min-heap priority queue (inverted for max-score-first execution).

    Supports dynamic reprioritisation and dependency checking.
    """

    def __init__(self) -> None:
        self._heap: list[tuple[float, int, Task]] = []  # (-score, seq, task)
        self._seq = 0
        self._completed: set[str] = set()

    def enqueue(self, task: Task) -> None:
        self._seq += 1
        heapq.heappush(self._heap, (-task.composite_score, self._seq, task))

    def dequeue_ready(self) -> Optional[Task]:
        """Pop the highest-scoring task whose dependencies are all complete."""
        candidates: list[tuple[float, int, Task]] = []
        result: Optional[Task] = None

        while self._heap:
            neg_score, seq, task = heapq.heappop(self._heap)
            if all(dep in self._completed for dep in task.dependencies):
                result = task
                # Re-queue unselected candidates
                for item in candidates:
                    heapq.heappush(self._heap, item)
                return result
            candidates.append((neg_score, seq, task))

        # No ready task found — re-queue candidates
        for item in candidates:
            heapq.heappush(self._heap, item)
        return None

    def mark_done(self, task_id: str) -> None:
        self._completed.add(task_id)

    @property
    def pending_count(self) -> int:
        return len(self._heap)


# ---------------------------------------------------------------------------
# Demo task backlog
# ---------------------------------------------------------------------------

_BACKLOG: list[dict[str, Any]] = [
    {"task_id": "T001", "title": "Critical production outage — API returning 500s",
     "description": "Users cannot log in. Revenue impact: ~$10k/hour.", "urgency": 10, "importance": 10, "priority": "critical"},
    {"task_id": "T002", "title": "Implement OAuth2 for the mobile app",
     "description": "Feature requested by 40% of users. Needed for enterprise contracts.", "urgency": 5, "importance": 9},
    {"task_id": "T003", "title": "Update internal wiki page",
     "description": "Outdated onboarding docs. Low user impact.", "urgency": 2, "importance": 3},
    {"task_id": "T004", "title": "Optimise slow database query (10s p95 latency)",
     "description": "Affects checkout flow. Customer complaints rising.", "urgency": 7, "importance": 8, "dependencies": ["T001"]},
    {"task_id": "T005", "title": "Write quarterly blog post",
     "description": "Marketing requested. No hard deadline.", "urgency": 2, "importance": 4},
    {"task_id": "T006", "title": "Security patch: update OpenSSL dependency",
     "description": "CVE-2024-XXXX. CVSS 8.1 — remote code execution possible.", "urgency": 9, "importance": 10},
]


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class PrioritizationPattern(BasePattern):
    """
    Demonstrates multi-framework task prioritization.

    Tasks are scored using Eisenhower Matrix + RICE, optionally enriched
    by LLM triage, then executed by a dependency-aware priority scheduler.
    """

    name = "20 · Prioritization"

    async def run(  # type: ignore[override]
        self,
        backlog: Optional[list[dict[str, Any]]] = None,
        use_llm_triage: bool = True,
    ) -> dict[str, Any]:
        self.print_header()

        if backlog is None:
            backlog = _BACKLOG

        # ── Build task objects ────────────────────────────────────────
        tasks = [Task(**{k: v for k, v in item.items() if k in Task.__dataclass_fields__}) for item in backlog]
        # Coerce priority strings to Priority enum (backlog dicts use plain strings)
        for t in tasks:
            if isinstance(t.priority, str):
                t.priority = Priority(t.priority) if t.priority in Priority._value2member_map_ else Priority.MEDIUM

        # ── LLM triage for tasks without manual scores ────────────────
        if use_llm_triage:
            triage_needed = [t for t in tasks if t.urgency == 5 and t.importance == 5]
            if triage_needed:
                self.print_step(
                    "LLM Triage",
                    f"Auto-scoring {len(triage_needed)} tasks with LLM…",
                )
                await asyncio.gather(*[llm_triage_task(self.client, t) for t in triage_needed])

        # ── Score all tasks ───────────────────────────────────────────
        for t in tasks:
            t.score_all()

        # ── Display scoring ───────────────────────────────────────────
        sorted_tasks = sorted(tasks, key=lambda t: t.composite_score, reverse=True)
        score_table = "\n".join(
            f"  [{t.priority.value.upper():8}] {t.composite_score:6.1f}  "
            f"RICE={t.rice_score:5.1f}  {t.quadrant.value if t.quadrant else '?':45}  {t.title}"
            for t in sorted_tasks
        )
        self.print_step("Scored & Ranked Backlog", score_table)

        # ── Load priority scheduler ───────────────────────────────────
        scheduler = PriorityScheduler()
        for t in sorted_tasks:
            scheduler.enqueue(t)

        # ── Execute tasks ─────────────────────────────────────────────
        executed: list[Task] = []
        blocked:  list[Task] = []

        while scheduler.pending_count > 0:
            task = scheduler.dequeue_ready()
            if task is None:
                # All remaining tasks are blocked by unresolved dependencies
                blocked = [item[2] for item in scheduler._heap]
                break

            task.status = "in_progress"
            self.print_step(
                f"Execute [{task.priority.value.upper()}] {task.title}",
                f"Composite: {task.composite_score}  |  Quadrant: {task.quadrant.value if task.quadrant else '?'}",
            )

            # LLM executes the task
            task.result = await self.client.complete_text(
                f"Task: {task.title}\n{task.description}\n\nComplete this task concisely (50–80 words).",
                system="You are a diligent engineer completing tasks efficiently.",
                max_tokens=150,
            )
            self.print_step(f"  Result", task.result)
            task.status = "done"
            scheduler.mark_done(task.task_id)
            executed.append(task)

        # ── Summary ───────────────────────────────────────────────────
        if blocked:
            self.print_step(
                "Blocked Tasks (unresolved dependencies)",
                "\n".join(f"  {t.task_id}: {t.title}  deps={t.dependencies}" for t in blocked),
            )

        self.print_result(
            f"Executed: {len(executed)}/{len(tasks)}  |  "
            f"Blocked: {len(blocked)}  |  "
            f"Top priority: {executed[0].title if executed else 'none'}"
        )

        return {
            "total_tasks": len(tasks),
            "executed": len(executed),
            "blocked": len(blocked),
            "execution_order": [t.task_id for t in executed],
            "top_task": executed[0].title if executed else "",
        }
