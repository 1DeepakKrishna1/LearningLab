"""DOK-based question generation using Webb's Depth of Knowledge framework."""

from __future__ import annotations

from typing import Any

import yaml

from src.enrichment.groq_client import GroqClient
from src.models.schemas import DOKQuestion, DOKQuestions, TextChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DOKQuestionGenerator:
    """Generates questions at all four DOK cognitive levels per document chunk."""

    def __init__(
        self,
        groq_client: GroqClient,
        questions_per_level: int = 3,
        active_levels: list[int] = None,
        prompts_path: str = "config/prompts.yaml",
    ) -> None:
        self.groq = groq_client
        self.questions_per_level = questions_per_level
        self.active_levels = set(active_levels or [1, 2, 3, 4])
        with open(prompts_path, "r", encoding="utf-8") as f:
            prompts = yaml.safe_load(f)
        self.prompts = prompts.get("dok_questions", {})

    def generate(
        self,
        chunks: list[TextChunk],
        doc_id: str,
        doc_title: str = "",
        topics: list[str] = None,
    ) -> DOKQuestions:
        """Generate and aggregate DOK questions across all chunks."""
        aggregate = DOKQuestions(doc_id=doc_id)
        topics_str = ", ".join(topics or [])

        for chunk in chunks:
            chunk_qs = self._process_chunk(chunk, doc_id, doc_title, topics_str)
            if chunk_qs:
                aggregate.level_1.extend(chunk_qs.level_1)
                aggregate.level_2.extend(chunk_qs.level_2)
                aggregate.level_3.extend(chunk_qs.level_3)
                aggregate.level_4.extend(chunk_qs.level_4)

        logger.info(
            "dok_questions_generated",
            doc_id=doc_id,
            l1=len(aggregate.level_1),
            l2=len(aggregate.level_2),
            l3=len(aggregate.level_3),
            l4=len(aggregate.level_4),
        )
        return aggregate

    def _process_chunk(
        self, chunk: TextChunk, doc_id: str, doc_title: str, topics_str: str
    ) -> DOKQuestions | None:
        system = self.prompts.get("system", "")
        user = self.prompts.get("user", "").format(
            doc_title=doc_title,
            topics=topics_str,
            questions_per_level=self.questions_per_level,
            text=chunk.text,
        )

        data = self.groq.complete_json(system, user, call_type="dok_questions")
        if not data or not isinstance(data, dict):
            return None

        return self._parse_dok(data, chunk.chunk_id)

    def _parse_dok(self, data: dict[str, Any], chunk_id: str) -> DOKQuestions:
        dok = DOKQuestions(doc_id="")

        for level_key in ("level_1", "level_2", "level_3", "level_4"):
            level_num = int(level_key.split("_")[1])
            if level_num not in self.active_levels:
                continue
            items = data.get(level_key, [])
            parsed: list[DOKQuestion] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                try:
                    parsed.append(
                        DOKQuestion(
                            question=item.get("question", ""),
                            answer=item.get("answer", ""),
                            bloom=item.get("bloom"),
                            chunk_id=chunk_id,
                        )
                    )
                except Exception:
                    pass
            setattr(dok, level_key, parsed)

        return dok
