"""
Pattern 9 – Learning and Adaptation
======================================
The agent observes explicit feedback on its responses, builds a
``PreferenceProfile``, and dynamically adapts its behaviour on
subsequent requests by injecting the learned preferences into its
system prompt.

Learning loop in this demo:
  Round 1: generate response with default style
  → user provides feedback (simulated)
  Round 2: regenerate with updated preference profile injected
  → user provides further feedback
  Round 3: final response demonstrating full adaptation
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from llm_client import GroqClient, FAST_MODEL
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feedback & preference models
# ---------------------------------------------------------------------------


@dataclass
class FeedbackEntry:
    """A single piece of user feedback on an agent response."""

    prompt: str
    response: str
    rating: int       # 1 (poor) – 5 (excellent)
    comment: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class PreferenceProfile:
    """
    Accumulated user preferences derived from feedback.

    Attributes:
        style_notes:    Qualitative preferences about tone and style.
        length_pref:    "concise" | "moderate" | "detailed"
        format_pref:    "prose" | "bullets" | "structured"
        avoid:          Patterns the user dislikes.
        strengths:      Things the user appreciated.
        feedback_count: Total feedback entries processed.
    """

    style_notes: list[str] = field(default_factory=list)
    length_pref: str = "moderate"
    format_pref: str = "prose"
    avoid: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    feedback_count: int = 0

    def to_system_injection(self) -> str:
        """Render the profile as a system-prompt instruction block."""
        if self.feedback_count == 0:
            return ""
        parts = [
            "--- Learned User Preferences ---",
            f"Length:  {self.length_pref}",
            f"Format:  {self.format_pref}",
        ]
        if self.style_notes:
            parts.append("Style:   " + "; ".join(self.style_notes))
        if self.strengths:
            parts.append("Keep:    " + "; ".join(self.strengths))
        if self.avoid:
            parts.append("Avoid:   " + "; ".join(self.avoid))
        parts.append("--------------------------------")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Preference updater
# ---------------------------------------------------------------------------

_UPDATER_SYSTEM = """\
You are a preference analyser. Given a user's feedback on an AI response,
extract updated preferences and return them as JSON with these exact keys:

{
  "style_notes":   [list of style observations],
  "length_pref":   "concise" | "moderate" | "detailed",
  "format_pref":   "prose" | "bullets" | "structured",
  "avoid":         [list of things to avoid],
  "strengths":     [list of things done well]
}

Return only valid JSON. Merge with existing preferences thoughtfully.
"""


class LearningAdaptationPattern(BasePattern):
    """
    Demonstrates feedback-driven learning and style adaptation.

    The agent generates a response, receives feedback (simulated here),
    updates its preference profile, and adapts the next response accordingly.
    """

    name = "9 · Learning and Adaptation"

    def __init__(self, client: GroqClient) -> None:
        super().__init__(client)
        self.profile = PreferenceProfile()
        self.feedback_log: list[FeedbackEntry] = []

    async def _update_profile(
        self,
        feedback: FeedbackEntry,
        current_profile: PreferenceProfile,
    ) -> PreferenceProfile:
        """Use the LLM to merge new feedback into the preference profile."""
        context = json.dumps(
            {
                "existing_profile": {
                    "style_notes": current_profile.style_notes,
                    "length_pref": current_profile.length_pref,
                    "format_pref": current_profile.format_pref,
                    "avoid": current_profile.avoid,
                    "strengths": current_profile.strengths,
                },
                "new_feedback": {
                    "rating": feedback.rating,
                    "comment": feedback.comment,
                },
            },
            indent=2,
        )
        raw = await self.client.complete_text(
            context,
            system=_UPDATER_SYSTEM,
            model=FAST_MODEL,
            temperature=0.2,
            max_tokens=400,
        )
        try:
            # Strip markdown fences if present
            import re
            clean = re.sub(r"```json\s*|\s*```", "", raw).strip()
            data = json.loads(clean)
            return PreferenceProfile(
                style_notes=data.get("style_notes", current_profile.style_notes),
                length_pref=data.get("length_pref", current_profile.length_pref),
                format_pref=data.get("format_pref", current_profile.format_pref),
                avoid=data.get("avoid", current_profile.avoid),
                strengths=data.get("strengths", current_profile.strengths),
                feedback_count=current_profile.feedback_count + 1,
            )
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Profile update parse failed: %s – keeping existing profile", exc)
            current_profile.feedback_count += 1
            return current_profile

    async def _generate(self, prompt: str, profile: PreferenceProfile) -> str:
        """Generate a response with the current preference profile injected."""
        pref_block = profile.to_system_injection()
        system = (
            "You are a helpful, adaptive assistant.\n\n"
            + (pref_block if pref_block else "No user preferences learned yet.")
        )
        return await self.client.complete_text(
            prompt,
            system=system,
            max_tokens=500,
        )

    async def run(  # type: ignore[override]
        self,
        prompt: str = "Explain the concept of recursion in programming.",
        feedback_rounds: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        self.print_header()
        print(f"Prompt: {prompt}\n")

        # Default simulated feedback rounds
        if feedback_rounds is None:
            feedback_rounds = [
                {
                    "rating": 2,
                    "comment": (
                        "Too long and verbose. I prefer concise bullet-point answers "
                        "with a short code example. Skip the lengthy introductions."
                    ),
                },
                {
                    "rating": 4,
                    "comment": (
                        "Much better! But please always include time/space complexity "
                        "when explaining algorithms."
                    ),
                },
            ]

        responses: list[dict[str, Any]] = []

        # ── Round 0: baseline (no learned preferences) ─────────────────
        self.print_step("Round 0 › Baseline Response (no preferences)", "Generating...")
        baseline = await self._generate(prompt, self.profile)
        self.print_step("Round 0 › Baseline Response", baseline)
        responses.append({"round": 0, "response": baseline, "profile_snapshot": None})

        # ── Feedback rounds ────────────────────────────────────────────
        for i, fb_data in enumerate(feedback_rounds, start=1):
            # Record feedback
            entry = FeedbackEntry(
                prompt=prompt,
                response=responses[-1]["response"],
                rating=fb_data["rating"],
                comment=fb_data["comment"],
            )
            self.feedback_log.append(entry)
            self.print_step(
                f"Feedback Round {i} › User Feedback",
                f"Rating: {entry.rating}/5\nComment: {entry.comment}",
            )

            # Update preference profile
            self.profile = await self._update_profile(entry, self.profile)
            self.print_step(
                f"Feedback Round {i} › Updated Preference Profile",
                self.profile.to_system_injection() or "(no preferences extracted yet)",
            )

            # Regenerate with updated preferences
            adapted = await self._generate(prompt, self.profile)
            self.print_step(f"Feedback Round {i} › Adapted Response", adapted)
            responses.append(
                {
                    "round": i,
                    "response": adapted,
                    "profile_snapshot": {
                        "length_pref": self.profile.length_pref,
                        "format_pref": self.profile.format_pref,
                        "style_notes": self.profile.style_notes,
                    },
                }
            )

        self.print_result(
            f"Completed {len(feedback_rounds)} adaptation round(s).\n"
            f"Final profile: length={self.profile.length_pref}, "
            f"format={self.profile.format_pref}, "
            f"feedback_count={self.profile.feedback_count}"
        )
        return {"prompt": prompt, "responses": responses, "final_profile": self.profile}
