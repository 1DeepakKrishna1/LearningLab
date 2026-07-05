"""Adapt discovered registry tools into OpenClaw (LangChain) tools.

An OpenClaw agent is a LangChain tool-calling agent. This module turns a set of
registry tool ids into ``StructuredTool`` instances whose execution is delegated
back to the :class:`ToolRegistry`, so there is one execution path for both the
workflow engine and agents (and one place that enforces the thread executor).

LangChain is imported lazily so the registry/engine work without it installed.
"""
from __future__ import annotations

from typing import Any

from ..domain.tool import ToolManifest
from ..logging_setup import get_logger
from .schema_builder import build_args_model
from .tool_registry import ToolRegistry

logger = get_logger("registry.openclaw")


def build_openclaw_tools(registry: ToolRegistry, tool_ids: list[str]) -> list[Any]:
    """Return LangChain ``StructuredTool`` objects for the given registry tool ids.

    Unknown ids are skipped with a warning. The allow-list enforcement happens in
    the agent runtime; here we simply build what we are asked for.
    """
    try:
        from langchain_core.tools import StructuredTool
    except ImportError:  # pragma: no cover - depends on optional dep
        logger.warning("langchain-core not installed; cannot build OpenClaw tools.")
        return []

    tools: list[Any] = []
    for tool_id in tool_ids:
        manifest: ToolManifest | None = registry.try_get(registry.normalise_id(tool_id))
        if manifest is None:
            logger.warning("Agent references unknown tool '%s' — skipped.", tool_id)
            continue

        args_model = build_args_model(manifest.id, manifest.parameters)
        # LangChain tool names must match ^[a-zA-Z0-9_-]+$.
        lc_name = manifest.id.replace(".", "__")

        async def _arun(__manifest_id: str = manifest.id, **kwargs: Any) -> str:
            result = await registry.execute(__manifest_id, kwargs)
            if result.get("status") == "error":
                return f"ERROR: {result.get('message', 'tool failed')}"
            data = result.get("data", result)
            return data if isinstance(data, str) else str(data)

        tools.append(
            StructuredTool(
                name=lc_name,
                description=manifest.description or manifest.display_name,
                args_schema=args_model,
                coroutine=_arun,
                func=None,
            )
        )
    return tools
