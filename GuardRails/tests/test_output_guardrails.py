"""Unit tests for all output guardrails."""
from __future__ import annotations

import json

import pytest

from guardrails.models.types import GuardrailStatus, PipelineContext
from tests.conftest import make_config


# ---------------------------------------------------------------------------
# JSONValidatorGuardrail
# ---------------------------------------------------------------------------

class TestJSONValidator:
    @pytest.fixture
    def guardrail(self):
        from guardrails.output.json_validator import JSONValidatorGuardrail
        return JSONValidatorGuardrail(make_config("json", sequence_id=1, required=False))

    @pytest.fixture
    def required_guardrail(self):
        from guardrails.output.json_validator import JSONValidatorGuardrail
        return JSONValidatorGuardrail(make_config("json", sequence_id=1, required=True))

    @pytest.mark.asyncio
    async def test_valid_json_passes(self, required_guardrail):
        result = await required_guardrail.execute('{"key": "value"}', PipelineContext())
        assert result.passed

    @pytest.mark.asyncio
    async def test_invalid_json_fails(self, required_guardrail):
        result = await required_guardrail.execute("{bad json}", PipelineContext())
        assert result.failed
        assert "INVALID_JSON" in result.flags

    @pytest.mark.asyncio
    async def test_non_json_skipped_when_not_required(self, guardrail):
        result = await guardrail.execute("This is plain text.", PipelineContext())
        assert result.status == GuardrailStatus.SKIP

    @pytest.mark.asyncio
    async def test_array_json_passes(self, required_guardrail):
        result = await required_guardrail.execute('[1, 2, 3]', PipelineContext())
        assert result.passed


# ---------------------------------------------------------------------------
# RedundancyRemovalGuardrail
# ---------------------------------------------------------------------------

class TestRedundancyRemoval:
    @pytest.fixture
    def guardrail(self):
        from guardrails.output.redundancy import RedundancyRemovalGuardrail
        return RedundancyRemovalGuardrail(
            make_config("red", sequence_id=8, similarity_threshold=0.8, min_sentence_length=10)
        )

    @pytest.mark.asyncio
    async def test_no_redundancy_passes_unchanged(self, guardrail):
        text = "The sky is blue. Water is wet. Fire is hot."
        result = await guardrail.execute(text, PipelineContext())
        assert result.passed
        assert result.modified_content is None

    @pytest.mark.asyncio
    async def test_duplicate_sentence_removed(self, guardrail):
        text = (
            "Python is a great programming language. "
            "Python is a great programming language. "
            "It supports many paradigms."
        )
        result = await guardrail.execute(text, PipelineContext())
        assert result.passed
        assert result.modified_content is not None
        # Only one copy should remain
        assert result.modified_content.count("Python is a great programming language") == 1


# ---------------------------------------------------------------------------
# ReadabilityGuardrail
# ---------------------------------------------------------------------------

class TestReadability:
    @pytest.fixture
    def guardrail(self):
        from guardrails.output.readability import ReadabilityGuardrail
        return ReadabilityGuardrail(
            make_config("read", sequence_id=16, min_score=0.0, max_score=100.0)
        )

    @pytest.mark.asyncio
    async def test_readable_text_passes(self, guardrail):
        text = "The cat sat on the mat. It was a nice day."
        result = await guardrail.execute(text, PipelineContext())
        assert result.passed
        assert result.score > 0

    @pytest.mark.asyncio
    async def test_empty_text_fails(self, guardrail):
        result = await guardrail.execute("", PipelineContext())
        assert result.failed

    @pytest.mark.asyncio
    async def test_metadata_populated(self, guardrail):
        ctx = PipelineContext()
        await guardrail.execute("The quick brown fox jumps.", ctx)
        assert "readability" in ctx.metadata
        assert "flesch_score" in ctx.metadata["readability"]

    @pytest.mark.asyncio
    async def test_score_below_min_fails(self):
        from guardrails.output.readability import ReadabilityGuardrail
        g = ReadabilityGuardrail(
            make_config("read", sequence_id=16, min_score=90.0, max_score=100.0)
        )
        text = (
            "The epistemological implications of quantum superposition necessitate "
            "a reconceptualisation of deterministic causal frameworks."
        )
        result = await g.execute(text, PipelineContext())
        assert result.failed


# ---------------------------------------------------------------------------
# ContentFilterGuardrail
# ---------------------------------------------------------------------------

class TestContentFilter:
    @pytest.fixture
    def guardrail(self):
        from guardrails.output.content_filter import ContentFilterGuardrail
        return ContentFilterGuardrail(make_config("cf", sequence_id=64))

    @pytest.mark.asyncio
    async def test_clean_output_passes(self, guardrail):
        result = await guardrail.execute(
            "Here is a helpful Python tutorial.", PipelineContext()
        )
        assert result.passed

    @pytest.mark.asyncio
    async def test_custom_pattern_detected(self):
        from guardrails.output.content_filter import ContentFilterGuardrail
        g = ContentFilterGuardrail(
            make_config(
                "cf",
                sequence_id=64,
                categories=[],
                extra_patterns={"CUSTOM": ["forbidden_word"]},
            )
        )
        result = await g.execute(
            "Here is a forbidden_word example.", PipelineContext()
        )
        assert result.failed
        assert "CUSTOM" in result.flags


# ---------------------------------------------------------------------------
# BrandSafetyGuardrail
# ---------------------------------------------------------------------------

class TestBrandSafety:
    @pytest.fixture
    def guardrail(self):
        from guardrails.output.brand_safety import BrandSafetyGuardrail
        return BrandSafetyGuardrail(
            make_config(
                "brand",
                sequence_id=128,
                competitors=["CompetitorX"],
                block_on_competitor_mention=True,
            )
        )

    @pytest.mark.asyncio
    async def test_no_competitor_passes(self, guardrail):
        result = await guardrail.execute("Our product is great.", PipelineContext())
        assert result.passed

    @pytest.mark.asyncio
    async def test_competitor_mention_fails_when_blocking(self, guardrail):
        result = await guardrail.execute(
            "You should use CompetitorX instead.", PipelineContext()
        )
        assert result.failed
        assert any("COMPETITOR" in f for f in result.flags)

    @pytest.mark.asyncio
    async def test_no_config_skips(self):
        from guardrails.output.brand_safety import BrandSafetyGuardrail
        g = BrandSafetyGuardrail(make_config("brand", sequence_id=128))
        result = await g.execute("Anything here.", PipelineContext())
        assert result.status == GuardrailStatus.SKIP


# ---------------------------------------------------------------------------
# LogicalConsistencyGuardrail (LLM-based)
# ---------------------------------------------------------------------------

class TestLogicalConsistency:
    @pytest.mark.asyncio
    async def test_skips_without_llm(self):
        from guardrails.output.consistency import LogicalConsistencyGuardrail
        g = LogicalConsistencyGuardrail(make_config("cons", sequence_id=4))
        result = await g.execute("Some response.", PipelineContext())
        assert result.status == GuardrailStatus.SKIP

    @pytest.mark.asyncio
    async def test_passes_with_llm_pass(self, pass_llm):
        from guardrails.output.consistency import LogicalConsistencyGuardrail
        g = LogicalConsistencyGuardrail(
            make_config("cons", sequence_id=4), llm_client=pass_llm
        )
        ctx = PipelineContext(original_input="What is 2+2?")
        result = await g.execute("The answer is 4.", ctx)
        assert result.passed
