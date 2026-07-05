"""Parse a tool's README.md into structured metadata.

The library's READMEs follow a consistent convention:

    # Display Name
    <one-paragraph description>
    ## Input Parameters
    | Parameter | Type | Required | Default | Description |
    |-----------|------|----------|---------|-------------|
    | to        | string or list | Yes | — | ... |
    ## Return Value
    | Field | Type | Description |
    |-------|------|-------------|
    | status | string | "success" or "error" |
    ## Example
    ```json
    { ... }
    ```

This parser is defensive: missing sections degrade gracefully rather than raising.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

_TRUE = {"yes", "true", "required", "y"}
_EMPTY = {"", "—", "-", "–", "n/a", "none", "null"}


@dataclass
class ParsedReadme:
    display_name: str = ""
    description: str = ""
    parameters: list[dict[str, Any]] = field(default_factory=list)
    returns: list[dict[str, Any]] = field(default_factory=list)
    examples: list[Any] = field(default_factory=list)


def _split_row(line: str) -> list[str]:
    """Split a markdown table row into trimmed cells."""
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def _is_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|?\s*:?-{2,}", line)) and set(line.strip()) <= set("|-: ")


def _parse_table(lines: list[str], start: int) -> tuple[list[dict[str, str]], int]:
    """Parse a GitHub-flavoured markdown table starting at `start` (header row).

    Returns the list of row dicts (keyed by lowercased header) and the index of the
    first line after the table.
    """
    if start >= len(lines):
        return [], start
    headers = [h.lower() for h in _split_row(lines[start])]
    idx = start + 1
    if idx < len(lines) and _is_separator(lines[idx]):
        idx += 1
    rows: list[dict[str, str]] = []
    while idx < len(lines):
        line = lines[idx]
        if "|" not in line or not line.strip():
            break
        cells = _split_row(line)
        if len(cells) < len(headers):
            cells += [""] * (len(headers) - len(cells))
        rows.append({headers[i]: cells[i] for i in range(len(headers))})
        idx += 1
    return rows, idx


def _clean_default(raw: str) -> Any:
    raw = raw.strip().strip("`").strip('"')
    if raw.lower() in _EMPTY:
        return None
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    return raw


def _normalise_param(row: dict[str, str]) -> dict[str, Any] | None:
    name = (row.get("parameter") or row.get("name") or row.get("field") or "").strip().strip("`")
    if not name:
        return None
    required = (row.get("required", "") or "").strip().lower() in _TRUE
    return {
        "name": name,
        "type": (row.get("type", "string") or "string").strip().lower() or "string",
        "required": required,
        "default": _clean_default(row.get("default", "")),
        "description": (row.get("description") or "").strip(),
    }


def _extract_json_blocks(text: str) -> list[Any]:
    blocks: list[Any] = []
    for match in re.finditer(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL):
        snippet = match.group(1).strip()
        if not snippet.startswith(("{", "[")):
            continue
        try:
            blocks.append(json.loads(snippet))
        except json.JSONDecodeError:
            continue
    return blocks


def parse_readme(text: str) -> ParsedReadme:
    """Parse README markdown text into a :class:`ParsedReadme`."""
    result = ParsedReadme()
    lines = text.splitlines()

    # Title (first H1) and description (first non-empty paragraph after it).
    for i, line in enumerate(lines):
        if line.startswith("# "):
            result.display_name = line[2:].strip()
            for j in range(i + 1, len(lines)):
                stripped = lines[j].strip()
                if not stripped:
                    continue
                if stripped.startswith(("#", "|", "```")):
                    break
                result.description = stripped
                break
            break

    # Walk sections, parsing the table under the first heading whose title matches.
    i = 0
    current: str | None = None
    while i < len(lines):
        line = lines[i]
        heading = re.match(r"^#{2,}\s+(.*)$", line)
        if heading:
            current = heading.group(1).strip().lower()
            i += 1
            continue
        if "|" in line and line.strip().startswith("|"):
            rows, nxt = _parse_table(lines, i)
            if current and ("input" in current or "parameter" in current):
                result.parameters = [p for r in rows if (p := _normalise_param(r))]
            elif current and ("return" in current or "output" in current):
                for r in rows:
                    fld = (r.get("field") or r.get("parameter") or r.get("name") or "").strip().strip("`")
                    if fld:
                        result.returns.append({
                            "field": fld,
                            "type": (r.get("type", "string") or "string").strip().lower(),
                            "description": (r.get("description") or "").strip(),
                        })
            i = nxt
            continue
        i += 1

    result.examples = _extract_json_blocks(text)
    return result
