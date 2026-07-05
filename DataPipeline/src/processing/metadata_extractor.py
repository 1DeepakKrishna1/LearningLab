"""Metadata extraction: NER, keywords, topics from document text."""

from __future__ import annotations

from typing import Any, Optional

from src.models.schemas import DocumentMetadata
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MetadataExtractor:
    """Extracts rich metadata (NER entities, keywords, topics) from document text.

    Uses spaCy for NER and KeyBERT for keyword extraction. Models are loaded
    lazily to avoid startup overhead when not needed.
    """

    def __init__(
        self,
        ner_model: str = "en_core_web_sm",
        max_keywords: int = 15,
    ) -> None:
        self.ner_model = ner_model
        self.max_keywords = max_keywords
        self._nlp: Any = None
        self._kw_model: Any = None

    def _get_nlp(self):
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load(self.ner_model)
            except OSError:
                import spacy
                from spacy.cli import download
                logger.info("downloading_spacy_model", model=self.ner_model)
                download(self.ner_model)
                self._nlp = spacy.load(self.ner_model)
        return self._nlp

    def _get_kw_model(self):
        if self._kw_model is None:
            try:
                from keybert import KeyBERT
                self._kw_model = KeyBERT()
            except ImportError as e:
                raise ImportError("keybert not installed. Run: pip install keybert") from e
        return self._kw_model

    def extract(
        self,
        text: str,
        pdf_metadata: dict[str, Any],
        total_pages: int,
    ) -> DocumentMetadata:
        """Extract all metadata from document text and PDF metadata dict."""
        word_count = len(text.split())

        title = (
            pdf_metadata.get("title")
            or self._infer_title(text)
            or "Untitled"
        )
        author = pdf_metadata.get("author") or ""

        entities = self._extract_entities(text[:50_000])  # cap for performance
        keywords = self._extract_keywords(text[:30_000])
        topics = self._infer_topics(keywords, entities)

        return DocumentMetadata(
            title=title,
            author=author,
            keywords=keywords,
            topics=topics,
            entities=entities,
            page_count=total_pages,
            word_count=word_count,
        )

    def _extract_entities(self, text: str) -> list[dict[str, str]]:
        try:
            nlp = self._get_nlp()
            doc = nlp(text)
            seen: set[str] = set()
            entities: list[dict[str, str]] = []
            for ent in doc.ents:
                key = (ent.text.strip().lower(), ent.label_)
                if key not in seen and len(ent.text.strip()) > 1:
                    seen.add(key)
                    entities.append({"text": ent.text.strip(), "label": ent.label_})
            return entities[:100]
        except Exception as exc:
            logger.warning("ner_failed", error=str(exc))
            return []

    def _extract_keywords(self, text: str) -> list[str]:
        try:
            kw_model = self._get_kw_model()
            keywords = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),
                stop_words="english",
                top_n=self.max_keywords,
                use_maxsum=True,
                nr_candidates=30,
            )
            return [kw for kw, _ in keywords]
        except Exception as exc:
            logger.warning("keyword_extraction_failed", error=str(exc))
            return []

    @staticmethod
    def _infer_title(text: str) -> Optional[str]:
        """Use the first non-empty line as a fallback title."""
        for line in text.splitlines():
            line = line.strip()
            if len(line) > 5 and len(line) < 200:
                return line
        return None

    @staticmethod
    def _infer_topics(keywords: list[str], entities: list[dict]) -> list[str]:
        """Derive a short topics list from top keywords and prominent entities."""
        topics: list[str] = []
        org_entities = [e["text"] for e in entities if e.get("label") in ("ORG", "PRODUCT", "GPE")]
        topics.extend(org_entities[:5])
        topics.extend(keywords[:5])
        return list(dict.fromkeys(topics))[:10]
