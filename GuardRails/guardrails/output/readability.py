"""Complexity & Readability Scoring guardrail (sequence_id = 16)."""
from __future__ import annotations

import re
from typing import Optional

from guardrails.base.guardrail import OutputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

_VOWELS = re.compile(r"[aeiouy]+", re.IGNORECASE)
_SENTENCE_END = re.compile(r"[.!?]+")
_WORD = re.compile(r"\b[a-zA-Z'-]{1,}\b")


def _count_syllables(word: str) -> int:
    """Approximate syllable count using vowel-group heuristic."""
    word = word.lower().rstrip("e")
    count = len(_VOWELS.findall(word))
    return max(1, count)


def _flesch_reading_ease(text: str) -> Tuple[float, int, int, int]:
    words = _WORD.findall(text)
    sentences = [s.strip() for s in _SENTENCE_END.split(text) if s.strip()]
    n_words = max(1, len(words))
    n_sentences = max(1, len(sentences))
    n_syllables = sum(_count_syllables(w) for w in words)

    # Flesch Reading Ease (0–100; higher = easier)
    score = 206.835 - 1.015 * (n_words / n_sentences) - 84.6 * (n_syllables / n_words)
    score = max(0.0, min(100.0, score))
    return score, n_words, n_sentences, n_syllables


# Avoid NameError from the Tuple reference before runtime (Python < 3.9)
from typing import Tuple  # noqa: E402


def _grade_label(score: float) -> str:
    if score >= 90:
        return "Very Easy (5th grade)"
    if score >= 70:
        return "Easy (7th grade)"
    if score >= 60:
        return "Standard (8–9th grade)"
    if score >= 50:
        return "Fairly Difficult (10–12th grade)"
    if score >= 30:
        return "Difficult (College)"
    return "Very Difficult (Professional)"


class ReadabilityGuardrail(OutputGuardrail):
    """Scores output readability using the Flesch Reading Ease formula.

    No external dependencies required.

    Parameters:
        min_score (float, default 0.0): Minimum acceptable Flesch score (0–100).
        max_score (float, default 100.0): Maximum acceptable Flesch score.
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._min_score: float = config.parameters.get("min_score", 0.0)
        self._max_score: float = config.parameters.get("max_score", 100.0)

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        if not content.strip():
            return self._fail_result(score=0.0, message="Empty output", flags=["EMPTY"])

        flesch, n_words, n_sentences, n_syllables = _flesch_reading_ease(content)
        grade = _grade_label(flesch)
        normalised = flesch / 100.0

        context.metadata["readability"] = {
            "flesch_score": round(flesch, 2),
            "grade": grade,
            "word_count": n_words,
            "sentence_count": n_sentences,
            "syllable_count": n_syllables,
        }

        if flesch < self._min_score or flesch > self._max_score:
            return self._fail_result(
                score=normalised,
                message=(
                    f"Readability score {flesch:.1f} outside range "
                    f"[{self._min_score}, {self._max_score}]. Grade: {grade}"
                ),
                flags=["READABILITY_OUT_OF_RANGE"],
            )

        return self._pass_result(
            score=normalised,
            message=f"Readability score {flesch:.1f} — {grade}",
        )
