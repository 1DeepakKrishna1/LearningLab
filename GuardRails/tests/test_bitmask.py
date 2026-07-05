"""Tests for the bitmask-based guardrail activation logic."""
from __future__ import annotations

import pytest

from guardrails.base.guardrail import _validate_sequence_id
from guardrails.models.types import GuardrailConfig
from guardrails.registry.registry import GuardrailRegistry
from guardrails.utils.exceptions import RegistryError

from tests.conftest import make_config

# Lightweight concrete guardrail for structural tests only
from guardrails.input.prompt_injection import AntiPromptInjectionGuardrail
from guardrails.input.pii_detection import PIIDetectionGuardrail
from guardrails.input.sql_injection import SQLInjectionGuardrail


# ---------------------------------------------------------------------------
# sequence_id validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("valid_id", [1, 2, 4, 8, 16, 32, 64, 128, 256, 512])
def test_valid_sequence_ids(valid_id):
    _validate_sequence_id(valid_id)  # must not raise


@pytest.mark.parametrize("invalid_id", [0, -1, 3, 5, 6, 7, 9, 10, 100])
def test_invalid_sequence_ids(invalid_id):
    with pytest.raises(ValueError, match="power of 2"):
        _validate_sequence_id(invalid_id)


# ---------------------------------------------------------------------------
# is_active — bitmask check
# ---------------------------------------------------------------------------

def test_guardrail_active_when_bit_set():
    g = AntiPromptInjectionGuardrail(make_config("g", sequence_id=4))
    assert g.is_active(0b111) is True   # bit 4 is set in 7
    assert g.is_active(0b100) is True   # exact match
    assert g.is_active(0b011) is False  # bit 4 is NOT set in 3


def test_guardrail_inactive_when_bit_clear():
    g = PIIDetectionGuardrail(make_config("g", sequence_id=2))
    assert g.is_active(0b101) is False  # bit 2 is not set in 5
    assert g.is_active(0b010) is True


def test_all_active_with_full_mask():
    for seq in [1, 2, 4, 8, 16, 32]:
        g = AntiPromptInjectionGuardrail(make_config("g", sequence_id=seq))
        assert g.is_active(0xFFFF) is True


def test_none_active_with_zero_mask():
    for seq in [1, 2, 4, 8, 16, 32]:
        g = AntiPromptInjectionGuardrail(make_config("g", sequence_id=seq))
        assert g.is_active(0) is False


# ---------------------------------------------------------------------------
# Registry bitmask filtering
# ---------------------------------------------------------------------------

def test_registry_returns_correct_subset():
    registry = GuardrailRegistry()
    registry.register(AntiPromptInjectionGuardrail(make_config("inj", sequence_id=1)))
    registry.register(PIIDetectionGuardrail(make_config("pii", sequence_id=2)))
    registry.register(SQLInjectionGuardrail(make_config("sql", sequence_id=16)))

    # mapped_number=3 → bits 1+2 active, bit 16 NOT active
    result = registry.get_input_guardrails(mapped_number=3)
    names = [g.name for g in result]
    assert "inj" in names
    assert "pii" in names
    assert "sql" not in names


def test_registry_returns_all_with_full_mask():
    registry = GuardrailRegistry()
    registry.register(AntiPromptInjectionGuardrail(make_config("inj", sequence_id=1)))
    registry.register(PIIDetectionGuardrail(make_config("pii", sequence_id=2)))
    registry.register(SQLInjectionGuardrail(make_config("sql", sequence_id=16)))

    result = registry.get_input_guardrails(mapped_number=0xFFFF)
    assert len(result) == 3


def test_registry_returns_none_with_zero_mask():
    registry = GuardrailRegistry()
    registry.register(AntiPromptInjectionGuardrail(make_config("inj", sequence_id=1)))

    result = registry.get_input_guardrails(mapped_number=0)
    assert result == []


def test_registry_rejects_duplicate_sequence_id():
    registry = GuardrailRegistry()
    registry.register(AntiPromptInjectionGuardrail(make_config("first", sequence_id=1)))
    with pytest.raises(RegistryError, match="already registered"):
        registry.register(PIIDetectionGuardrail(make_config("second", sequence_id=1)))


def test_registry_disabled_guardrail_excluded():
    registry = GuardrailRegistry()
    cfg = make_config("disabled", sequence_id=1)
    cfg.enabled = False
    registry.register(AntiPromptInjectionGuardrail(cfg))

    result = registry.get_input_guardrails(mapped_number=0xFFFF)
    assert result == []
