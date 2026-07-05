"""Discovery against the real agents-tools-library."""
from pathlib import Path

import pytest

from app.registry.discovery import discover_tools

LIB = Path(__file__).resolve().parents[4] / "agents_tools_library" / "library"
pytestmark = pytest.mark.skipif(not LIB.exists(), reason="tool library not present")


def test_discovers_many_tools():
    manifests = discover_tools(LIB)
    assert len(manifests) > 100
    assert len({m.category for m in manifests}) >= 5


def test_send_email_fully_parsed():
    manifests = {m.id: m for m in discover_tools(LIB)}
    se = manifests["outlook.send_email"]
    assert se.class_name == "SendEmailTool"
    assert se.impl_path == "library.tools.outlook.send_email.tool"
    assert se.input_schema["required"] == ["to", "subject"]
    assert any(p.name == "is_html" for p in se.parameters)
    assert se.node_type == "tool.outlook.send_email"


def test_every_readme_tool_has_params_or_no_readme():
    # Sanity: the parser should not silently drop params for documented tools.
    manifests = discover_tools(LIB)
    broken = [m.id for m in manifests if m.has_readme and m.parameters == []
              and m.category in {"outlook", "excel_tools", "pdf_tools"}]
    assert broken == [], f"README tools with no parsed params: {broken}"
