"""Small JSON read/write helpers with friendly errors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union

PathLike = Union[str, Path]


def write_json(path: PathLike, data: Any, *, indent: int = 2) -> Path:
    """Serialise ``data`` to ``path`` (creating parent dirs). Returns the path."""
    p = Path(path)
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent, ensure_ascii=False)
        fh.write("\n")
    return p


def read_json(path: PathLike) -> Any:
    """Load JSON from ``path``, raising a clear error if missing/invalid."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    try:
        with p.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:  # pragma: no cover - exercised via CLI
        raise ValueError(f"Invalid JSON in {p}: {exc}") from exc
