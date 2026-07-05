"""Execution context shared across nodes during a run.

Holds the trigger payload, workflow variables, and each completed node's output.
Provides ``{{ ... }}`` template interpolation so node configs can reference upstream
data, e.g. ``{{ trigger.payload.email }}`` or ``{{ nodes.n2.output.data }}``.
"""
from __future__ import annotations

import re
from typing import Any

_TEMPLATE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


class ExecutionContext:
    """Mutable run state passed to every node handler."""

    def __init__(self, variables: dict[str, Any] | None = None,
                 trigger: dict[str, Any] | None = None) -> None:
        self.variables: dict[str, Any] = dict(variables or {})
        self.trigger: dict[str, Any] = dict(trigger or {})
        self.node_outputs: dict[str, Any] = {}

    def set_output(self, node_id: str, output: Any) -> None:
        self.node_outputs[node_id] = output

    def snapshot(self) -> dict[str, Any]:
        return {
            "variables": dict(self.variables),
            "trigger": dict(self.trigger),
            "nodes": {k: {"output": v} for k, v in self.node_outputs.items()},
        }

    def _resolve_path(self, path: str) -> Any:
        cur: Any = self.snapshot()
        for part in re.split(r"\.|\[|\]", path):
            part = part.strip().strip("'\"")
            if part == "":
                continue
            try:
                if isinstance(cur, dict):
                    cur = cur.get(part)
                elif isinstance(cur, (list, tuple)) and part.isdigit():
                    cur = cur[int(part)]
                else:
                    cur = getattr(cur, part, None)
            except Exception:  # noqa: BLE001
                return None
            if cur is None:
                return None
        return cur

    def interpolate(self, value: Any) -> Any:
        """Recursively resolve ``{{ path }}`` templates inside strings/dicts/lists."""
        if isinstance(value, str):
            # Whole-string single template → preserve native type.
            whole = _TEMPLATE.fullmatch(value.strip())
            if whole:
                return self._resolve_path(whole.group(1))
            return _TEMPLATE.sub(lambda m: str(self._resolve_path(m.group(1)) or ""), value)
        if isinstance(value, dict):
            return {k: self.interpolate(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.interpolate(v) for v in value]
        return value
