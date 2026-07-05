"""Redundancy Removal guardrail (sequence_id = 8)."""
from __future__ import annotations

import re
from typing import List, Set, Tuple

from guardrails.base.guardrail import OutputGuardrail
from guardrails.models.types import GuardrailConfig, GuardrailResult, PipelineContext

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _tokenize(sentence: str) -> Set[str]:
    return set(re.sub(r"[^a-z0-9\s]", "", sentence.lower()).split())


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


class RedundancyRemovalGuardrail(OutputGuardrail):
    """Detects and removes near-duplicate sentences from LLM output.

    Deduplication uses Jaccard similarity on token sets.  The modified
    (de-duplicated) text is passed forward in the pipeline via
    ``modified_content``.

    Parameters:
        similarity_threshold (float, default 0.85): Sentences with Jaccard
            similarity above this are considered duplicates.
        min_sentence_length (int, default 15): Ignore sentences shorter than
            this (punctuation artefacts, etc.).
    """

    def __init__(self, config: GuardrailConfig, **kwargs) -> None:
        super().__init__(config, **kwargs)
        self._threshold: float = config.parameters.get("similarity_threshold", 0.85)
        self._min_len: int = config.parameters.get("min_sentence_length", 15)

    async def _execute(self, content: str, context: PipelineContext) -> GuardrailResult:
        sentences: List[str] = [s.strip() for s in _SENT_SPLIT.split(content) if s.strip()]

        kept: List[str] = []
        kept_tokens: List[Set[str]] = []
        removed: List[str] = []

        for sent in sentences:
            if len(sent) < self._min_len:
                kept.append(sent)
                kept_tokens.append(_tokenize(sent))
                continue

            tokens = _tokenize(sent)
            is_duplicate = any(
                _jaccard(tokens, prev) >= self._threshold for prev in kept_tokens
            )
            if is_duplicate:
                removed.append(sent)
            else:
                kept.append(sent)
                kept_tokens.append(tokens)

        if not removed:
            return self._pass_result(score=1.0, message="No redundancy detected")

        deduped = " ".join(kept)
        redundancy_ratio = len(removed) / len(sentences)
        return self._pass_result(
            score=1.0 - redundancy_ratio,
            message=f"Removed {len(removed)} redundant sentence(s)",
            modified_content=deduped,
        )
