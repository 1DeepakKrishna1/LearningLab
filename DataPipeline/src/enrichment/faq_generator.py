"""FAQ generation from document chunks using GroQ LLM."""

from __future__ import annotations

from typing import Any

import yaml

from src.enrichment.groq_client import GroqClient
from src.models.schemas import FAQPair, TextChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FAQGenerator:
    """Generates high-quality FAQ pairs from document chunks."""

    def __init__(
        self,
        groq_client: GroqClient,
        pairs_per_chunk: int = 5,
        prompts_path: str = "config/prompts.yaml",
    ) -> None:
        self.groq = groq_client
        self.pairs_per_chunk = pairs_per_chunk
        with open(prompts_path, "r", encoding="utf-8") as f:
            prompts = yaml.safe_load(f)
        self.prompts = prompts.get("faq", {})

    def generate(
        self,
        chunks: list[TextChunk],
        doc_id: str,
        doc_title: str = "",
        topics: list[str] = None,
        keywords: list[str] = None,
    ) -> list[FAQPair]:
        """Generate FAQ pairs across all document chunks and return deduplicated list."""
        all_faqs: list[FAQPair] = []
        topics_str = ", ".join(topics or [])
        keywords_str = ", ".join(keywords or [])

        for chunk in chunks:
            chunk_faqs = self._process_chunk(
                chunk, doc_id, doc_title, topics_str, keywords_str
            )
            all_faqs.extend(chunk_faqs)

        deduplicated = self._deduplicate(all_faqs)
        logger.info("faqs_generated", doc_id=doc_id, total=len(deduplicated))
        return deduplicated

    def _process_chunk(
        self,
        chunk: TextChunk,
        doc_id: str,
        doc_title: str,
        topics_str: str,
        keywords_str: str,
    ) -> list[FAQPair]:
        system = self.prompts.get("system", "")
        user = self.prompts.get("user", "").format(
            num_pairs=self.pairs_per_chunk,
            doc_title=doc_title,
            topics=topics_str,
            keywords=keywords_str,
            text=chunk.text,
        )

        data = self.groq.complete_json(system, user, call_type="faq")
        if not data or not isinstance(data, list):
            return []

        faqs: list[FAQPair] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                faqs.append(
                    FAQPair(
                        question=item.get("question", ""),
                        answer=item.get("answer", ""),
                        category=item.get("category"),
                        confidence=float(item.get("confidence", 1.0)),
                        chunk_id=chunk.chunk_id,
                        doc_id=doc_id,
                    )
                )
            except Exception as exc:
                logger.debug("faq_parse_error", error=str(exc))

        return faqs

    @staticmethod
    def _deduplicate(faqs: list[FAQPair]) -> list[FAQPair]:
        """Remove FAQ pairs with near-identical questions (exact match dedup)."""
        seen: set[str] = set()
        unique: list[FAQPair] = []
        for faq in faqs:
            key = faq.question.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(faq)
        return unique
