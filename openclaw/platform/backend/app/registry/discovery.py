"""Discover tools by scanning the agents-tools-library folder tree.

Layout assumed (matches the existing library):

    <library>/tools/<category>/<tool_folder>/
        ├── tool.py      # a BaseTool subclass
        ├── README.md    # capability docs (parsed for metadata)
        ├── main.py      # standalone runner (ignored)
        └── __init__.py

Discovery never imports tool modules (they may pull heavy/native deps such as
pywin32 or playwright). Metadata comes from README.md plus light source inspection
of tool.py (regex for the class name and the `name()`/`description()` literals).
"""
from __future__ import annotations

import re
from pathlib import Path

from ..domain.tool import ToolManifest, ToolParameter, ToolReturn
from ..logging_setup import get_logger
from .readme_parser import parse_readme
from .schema_builder import build_input_schema

logger = get_logger("registry.discovery")

# Heuristic icon/colour per known category for a nicer UI out of the box.
_CATEGORY_STYLE = {
    "outlook": ("mail", "#0078D4"),
    "excel_tools": ("table", "#217346"),
    "pdf_tools": ("file-text", "#D32F2F"),
    "web_tools": ("globe", "#F59E0B"),
    "pw_web_tools": ("globe", "#2563EB"),
    "data_storage_tools": ("database", "#0EA5E9"),
    "desktop_tools": ("monitor", "#7C3AED"),
    "api_tools": ("plug", "#10B981"),
    "rag_tools": ("brain", "#EC4899"),
}

_CLASS_RE = re.compile(r"class\s+(\w+)\s*\(\s*[\w.]*BaseTool\s*\)")
_NAME_RE = re.compile(r"def\s+name\s*\(self\)[^:]*:\s*(?:#.*\n\s*)*return\s+([\"'])(.*?)\1", re.DOTALL)
_DESC_RE = re.compile(r"def\s+description\s*\(self\)[^:]*:\s*return\s*\(?\s*([\"'])(.*?)\1", re.DOTALL)


def _inspect_source(tool_py: Path) -> tuple[str | None, str | None, str | None]:
    """Return (class_name, tool_name_literal, description_literal) from tool.py source."""
    try:
        src = tool_py.read_text(encoding="utf-8")
    except OSError:
        return None, None, None
    cls = m.group(1) if (m := _CLASS_RE.search(src)) else None
    name = m.group(2) if (m := _NAME_RE.search(src)) else None
    desc = m.group(2) if (m := _DESC_RE.search(src)) else None
    return cls, name, desc


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def discover_tool(tool_dir: Path, category: str, library_root: Path) -> ToolManifest | None:
    """Build a :class:`ToolManifest` for a single tool directory, or None if invalid."""
    tool_py = tool_dir / "tool.py"
    if not tool_py.exists():
        return None

    folder = tool_dir.name
    tool_id = f"{category}.{folder}"
    class_name, name_literal, desc_literal = _inspect_source(tool_py)

    # impl_path: dotted module path rooted at the importable `library` package.
    rel = tool_py.relative_to(library_root.parent).with_suffix("")
    impl_path = ".".join(rel.parts)

    readme_path = tool_dir / "README.md"
    has_readme = readme_path.exists()
    parsed = parse_readme(readme_path.read_text(encoding="utf-8")) if has_readme else None

    display_name = (parsed.display_name if parsed and parsed.display_name
                    else (name_literal or folder.replace("_", " ").title()))
    description = (parsed.description if parsed and parsed.description
                   else (desc_literal or ""))
    parameters = [ToolParameter(**p) for p in parsed.parameters] if parsed else []
    returns = [ToolReturn(**r) for r in parsed.returns] if parsed else []
    examples = parsed.examples if parsed else []

    icon, color = _CATEGORY_STYLE.get(category, ("wrench", "#6366F1"))
    tags = [category.replace("_tools", "").replace("_", " "), *(folder.split("_"))]

    return ToolManifest(
        id=tool_id,
        name=name_literal or folder,
        display_name=display_name,
        category=category,
        description=description,
        impl_path=impl_path,
        class_name=class_name,
        parameters=parameters,
        returns=returns,
        input_schema=build_input_schema(parameters),
        examples=examples,
        tags=sorted({t for t in tags if t}),
        icon=icon,
        color=color,
        source="readme" if has_readme else "introspection",
        has_readme=has_readme,
    )


def discover_tools(library_path: Path) -> list[ToolManifest]:
    """Scan ``<library_path>/tools/<category>/<tool>/`` and return all manifests."""
    tools_root = library_path / "tools"
    if not tools_root.exists():
        logger.warning("Tool library not found at %s", tools_root)
        return []

    manifests: list[ToolManifest] = []
    for category_dir in sorted(p for p in tools_root.iterdir() if p.is_dir()):
        if category_dir.name.startswith((".", "__")):
            continue
        for tool_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            if tool_dir.name.startswith((".", "__")):
                continue
            try:
                manifest = discover_tool(tool_dir, category_dir.name, library_path)
            except Exception as exc:  # one bad tool must not break discovery
                logger.exception("Failed to discover %s/%s: %s",
                                 category_dir.name, tool_dir.name, exc)
                continue
            if manifest:
                manifests.append(manifest)

    logger.info("Discovered %d tools across %d categories",
                len(manifests), len({m.category for m in manifests}))
    return manifests
