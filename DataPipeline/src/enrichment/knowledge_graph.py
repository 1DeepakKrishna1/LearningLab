"""Knowledge graph generation from document chunks using GroQ LLM."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.enrichment.groq_client import GroqClient
from src.models.schemas import (
    KGAttribute,
    KGEntity,
    KGRelationship,
    KnowledgeGraph,
    TextChunk,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _load_prompts(path: str = "config/prompts.yaml") -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class KnowledgeGraphGenerator:
    """Generates and merges a knowledge graph across all document chunks."""

    def __init__(self, groq_client: GroqClient, prompts_path: str = "config/prompts.yaml") -> None:
        self.groq = groq_client
        self.prompts = _load_prompts(prompts_path).get("knowledge_graph", {})

    def generate(
        self,
        chunks: list[TextChunk],
        doc_id: str,
        doc_title: str = "",
        topics: list[str] = None,
    ) -> KnowledgeGraph:
        """Generate a merged KG from all chunks of a document."""
        master = KnowledgeGraph(doc_id=doc_id)
        topics_str = ", ".join(topics or [])

        for chunk in chunks:
            chunk_kg = self._process_chunk(chunk, doc_title, topics_str)
            if chunk_kg:
                master.merge(chunk_kg)

        logger.info(
            "knowledge_graph_built",
            doc_id=doc_id,
            entities=len(master.entities),
            relationships=len(master.relationships),
        )
        return master

    def _process_chunk(
        self, chunk: TextChunk, doc_title: str, topics_str: str
    ) -> KnowledgeGraph | None:
        system = self.prompts.get("system", "")
        user = self.prompts.get("user", "").format(
            doc_title=doc_title,
            chunk_id=chunk.chunk_id,
            topics=topics_str,
            text=chunk.text,
        )

        data = self.groq.complete_json(system, user, call_type="knowledge_graph")
        if not data or not isinstance(data, dict):
            return None

        return self._parse_kg(data, chunk.doc_id)

    def _parse_kg(self, data: dict[str, Any], doc_id: str) -> KnowledgeGraph:
        entities: list[KGEntity] = []
        for e in data.get("entities", []):
            try:
                entities.append(KGEntity(**e))
            except Exception:
                pass

        relationships: list[KGRelationship] = []
        for r in data.get("relationships", []):
            try:
                relationships.append(KGRelationship(**r))
            except Exception:
                pass

        attributes: list[KGAttribute] = []
        for a in data.get("attributes", []):
            try:
                attributes.append(KGAttribute(**a))
            except Exception:
                pass

        return KnowledgeGraph(
            doc_id=doc_id,
            entities=entities,
            relationships=relationships,
            attributes=attributes,
        )
