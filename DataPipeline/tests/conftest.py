"""Shared pytest fixtures for the DataPipeline test suite."""

from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory that is cleaned up after each test."""
    return tmp_path


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> str:
    """Create a minimal single-page PDF and return its path."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet

        path = str(tmp_path / "test_document.pdf")
        doc = SimpleDocTemplate(path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Test Document Title", styles["Heading1"]),
            Paragraph(
                "Machine learning is a subset of artificial intelligence. "
                "It enables systems to learn from data automatically. "
                "Neural networks are used for deep learning tasks. "
                "Python is a popular programming language for data science. "
                "TensorFlow and PyTorch are popular deep learning frameworks.",
                styles["BodyText"],
            ),
        ]
        doc.build(story)
        return path
    except ImportError:
        pytest.skip("reportlab not installed")


@pytest.fixture
def sample_text() -> str:
    return (
        "Machine learning is a subset of artificial intelligence that enables systems "
        "to learn and improve from experience without being explicitly programmed.\n\n"
        "Supervised learning uses labeled training data to learn a mapping from inputs "
        "to outputs. Common algorithms include linear regression, decision trees, and "
        "support vector machines.\n\n"
        "Deep learning is a type of machine learning that uses neural networks with "
        "many layers to learn complex patterns in data. It has revolutionized computer "
        "vision, natural language processing, and speech recognition."
    )


@pytest.fixture
def mock_groq_response() -> dict[str, Any]:
    return {
        "entities": [
            {"id": "e1", "name": "Machine Learning", "type": "CONCEPT", "description": "AI subset"},
            {"id": "e2", "name": "Neural Network", "type": "CONCEPT", "description": "ML model"},
        ],
        "relationships": [
            {"source": "e1", "target": "e2", "relation": "uses", "confidence": 0.9}
        ],
        "attributes": [
            {"entity_id": "e1", "key": "domain", "value": "AI"}
        ],
    }


@pytest.fixture
def mock_faq_response() -> list[dict[str, Any]]:
    return [
        {
            "question": "What is machine learning?",
            "answer": "Machine learning is a subset of AI that enables systems to learn from data.",
            "category": "definition",
            "confidence": 0.95,
        }
    ]


@pytest.fixture
def file_store(tmp_dir: Path):
    from src.storage.file_store import FileStore
    return FileStore(str(tmp_dir / "output"))


@pytest.fixture
def deduplicator(tmp_dir: Path):
    from src.ingestion.deduplicator import Deduplicator
    return Deduplicator(str(tmp_dir / "dedup.json"))


@pytest.fixture
def metrics():
    from src.utils.metrics import PipelineMetrics
    return PipelineMetrics(enable_server=False)
