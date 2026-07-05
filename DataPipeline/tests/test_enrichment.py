"""Tests for the AI enrichment layer (GroQ client, KG, FAQ, DOK questions)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.models.schemas import TextChunk


def make_chunk(text: str = "Machine learning uses neural networks for predictions.") -> TextChunk:
    return TextChunk(
        chunk_id="test_chunk_0001",
        doc_id="doc_test",
        sequence=0,
        text=text,
    )


class TestGroqClient:
    def test_extract_json_from_plain_json(self) -> None:
        from src.enrichment.groq_client import GroqClient
        data = GroqClient._extract_json('{"key": "value"}')
        assert data == {"key": "value"}

    def test_extract_json_from_fenced_code(self) -> None:
        from src.enrichment.groq_client import GroqClient
        text = '```json\n{"entities": []}\n```'
        data = GroqClient._extract_json(text)
        assert data == {"entities": []}

    def test_extract_json_from_embedded_json(self) -> None:
        from src.enrichment.groq_client import GroqClient
        text = 'Here is the result: {"answer": 42} enjoy!'
        data = GroqClient._extract_json(text)
        assert data == {"answer": 42}

    def test_extract_json_returns_none_on_invalid(self) -> None:
        from src.enrichment.groq_client import GroqClient
        data = GroqClient._extract_json("this is not json at all!!!")
        assert data is None

    def test_extract_json_list(self) -> None:
        from src.enrichment.groq_client import GroqClient
        data = GroqClient._extract_json('[{"q": "a"}]')
        assert isinstance(data, list)


class TestKnowledgeGraphGenerator:
    def test_generate_returns_knowledge_graph(self, mock_groq_response) -> None:
        from src.enrichment.knowledge_graph import KnowledgeGraphGenerator
        from src.models.schemas import KnowledgeGraph

        mock_groq = MagicMock()
        mock_groq.complete_json.return_value = mock_groq_response

        generator = KnowledgeGraphGenerator(mock_groq)
        chunk = make_chunk()
        kg = generator.generate([chunk], "doc_test", "Test Doc", ["AI"])

        assert isinstance(kg, KnowledgeGraph)
        assert len(kg.entities) == 2
        assert len(kg.relationships) == 1

    def test_merge_deduplicates_entities(self) -> None:
        from src.models.schemas import KGEntity, KnowledgeGraph
        kg1 = KnowledgeGraph(doc_id="d1", entities=[KGEntity(id="e1", name="Python", type="CONCEPT")])
        kg2 = KnowledgeGraph(doc_id="d1", entities=[KGEntity(id="e2", name="Python", type="CONCEPT")])
        kg1.merge(kg2)
        assert len(kg1.entities) == 1

    def test_handles_llm_returning_none(self) -> None:
        from src.enrichment.knowledge_graph import KnowledgeGraphGenerator
        from src.models.schemas import KnowledgeGraph

        mock_groq = MagicMock()
        mock_groq.complete_json.return_value = None

        generator = KnowledgeGraphGenerator(mock_groq)
        kg = generator.generate([make_chunk()], "doc_x")
        assert isinstance(kg, KnowledgeGraph)
        assert len(kg.entities) == 0


class TestFAQGenerator:
    def test_generate_returns_faq_pairs(self, mock_faq_response) -> None:
        from src.enrichment.faq_generator import FAQGenerator
        from src.models.schemas import FAQPair

        mock_groq = MagicMock()
        mock_groq.complete_json.return_value = mock_faq_response

        generator = FAQGenerator(mock_groq, pairs_per_chunk=3)
        faqs = generator.generate([make_chunk()], "doc_test")

        assert len(faqs) == 1
        assert isinstance(faqs[0], FAQPair)
        assert faqs[0].question == "What is machine learning?"

    def test_deduplication_removes_identical_questions(self) -> None:
        from src.enrichment.faq_generator import FAQGenerator
        from src.models.schemas import FAQPair

        faqs = [
            FAQPair(question="What is AI?", answer="Artificial Intelligence"),
            FAQPair(question="What is AI?", answer="Another answer"),
            FAQPair(question="What is ML?", answer="Machine Learning"),
        ]
        unique = FAQGenerator._deduplicate(faqs)
        assert len(unique) == 2


class TestDOKQuestionGenerator:
    def test_generate_returns_dok_questions(self) -> None:
        from src.enrichment.question_generator import DOKQuestionGenerator
        from src.models.schemas import DOKQuestions

        mock_data = {
            "level_1": [{"question": "What is ML?", "answer": "Machine learning", "bloom": "Remember"}],
            "level_2": [{"question": "Explain supervised learning", "answer": "...", "bloom": "Understand"}],
            "level_3": [{"question": "Analyze bias-variance tradeoff", "answer": "...", "bloom": "Analyze"}],
            "level_4": [{"question": "Design an ML system", "answer": "...", "bloom": "Create"}],
        }
        mock_groq = MagicMock()
        mock_groq.complete_json.return_value = mock_data

        generator = DOKQuestionGenerator(mock_groq, questions_per_level=2)
        qs = generator.generate([make_chunk()], "doc_test")

        assert isinstance(qs, DOKQuestions)
        assert len(qs.level_1) == 1
        assert len(qs.level_2) == 1
        assert len(qs.level_3) == 1
        assert len(qs.level_4) == 1

    def test_handles_missing_levels_gracefully(self) -> None:
        from src.enrichment.question_generator import DOKQuestionGenerator
        from src.models.schemas import DOKQuestions

        mock_groq = MagicMock()
        mock_groq.complete_json.return_value = {"level_1": []}

        generator = DOKQuestionGenerator(mock_groq)
        qs = generator.generate([make_chunk()], "doc_test")
        assert isinstance(qs, DOKQuestions)
