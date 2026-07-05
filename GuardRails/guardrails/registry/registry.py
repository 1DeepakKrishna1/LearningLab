"""Central guardrail registry — register, discover, and query guardrails."""
from __future__ import annotations

import logging
from typing import Dict, List

from guardrails.base.guardrail import BaseGuardrail, InputGuardrail, OutputGuardrail
from guardrails.models.types import GuardrailType
from guardrails.utils.exceptions import RegistryError

logger = logging.getLogger(__name__)


class GuardrailRegistry:
    """Thread-safe-by-convention registry for input and output guardrails.

    Uniqueness is enforced per (type, sequence_id) pair so that the bitmask
    logic remains unambiguous.
    """

    def __init__(self) -> None:
        self._input: Dict[int, InputGuardrail] = {}
        self._output: Dict[int, OutputGuardrail] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, guardrail: BaseGuardrail) -> None:
        """Register a guardrail instance.  Raises RegistryError on duplicate."""
        seq_id = guardrail.sequence_id
        if guardrail.guardrail_type == GuardrailType.INPUT:
            self._check_duplicate(seq_id, self._input, "input")
            self._input[seq_id] = guardrail  # type: ignore[assignment]
        else:
            self._check_duplicate(seq_id, self._output, "output")
            self._output[seq_id] = guardrail  # type: ignore[assignment]
        logger.info(
            "Guardrail registered",
            extra={
                "guardrail_name": guardrail.name,
                "type": guardrail.guardrail_type,
                "sequence_id": seq_id,
            },
        )

    def unregister(self, sequence_id: int, guardrail_type: GuardrailType) -> None:
        store = self._input if guardrail_type == GuardrailType.INPUT else self._output
        if sequence_id not in store:
            raise RegistryError(
                f"No {guardrail_type} guardrail with sequence_id={sequence_id}"
            )
        del store[sequence_id]

    # ------------------------------------------------------------------
    # Discovery (bitmask-filtered)
    # ------------------------------------------------------------------

    def get_input_guardrails(self, mapped_number: int) -> List[InputGuardrail]:
        """Return active, enabled input guardrails ordered by sequence_id."""
        return [
            g
            for _, g in sorted(self._input.items())
            if g.is_active(mapped_number) and g.config.enabled
        ]

    def get_output_guardrails(self, mapped_number: int) -> List[OutputGuardrail]:
        """Return active, enabled output guardrails ordered by sequence_id."""
        return [
            g
            for _, g in sorted(self._output.items())
            if g.is_active(mapped_number) and g.config.enabled
        ]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_all(self) -> Dict[str, List[str]]:
        return {
            "input": [
                g.name for g in sorted(self._input.values(), key=lambda x: x.sequence_id)
            ],
            "output": [
                g.name for g in sorted(self._output.values(), key=lambda x: x.sequence_id)
            ],
        }

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    @staticmethod
    def _check_duplicate(
        seq_id: int, store: Dict[int, BaseGuardrail], label: str
    ) -> None:
        if seq_id in store:
            raise RegistryError(
                f"An {label} guardrail with sequence_id={seq_id} is already registered "
                f"('{store[seq_id].name}'). Each sequence_id must be unique within a type."
            )
