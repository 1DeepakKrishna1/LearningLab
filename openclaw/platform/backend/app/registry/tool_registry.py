"""In-memory tool registry with dynamic execution.

Responsibilities:
  * refresh()  — scan the library, build manifests, persist to tool_registry.json
  * lookup     — by id / category / search
  * execute()  — dynamically import the tool's class and run it (in a thread pool,
                 because tool `.run()` is synchronous and may block on COM/IO).

Adding a new tool to the library requires NO code change here: a refresh picks it up.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import importlib
import re
from pathlib import Path
from typing import Any

from ..config import Settings
from ..domain.tool import ToolManifest
from ..logging_setup import get_logger
from ..storage.repository import Repository
from .discovery import discover_tools

logger = get_logger("registry")

# A dedicated single-thread executor keeps stateful tools (e.g. Playwright's global
# browser, Outlook COM apartment) consistent across calls — mirrors the library's MCP server.
_TOOL_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="tool")


class ToolNotFoundError(KeyError):
    pass


class ToolRegistry:
    """Discovers, stores and executes library tools."""

    def __init__(self, settings: Settings, repo: Repository[ToolManifest]) -> None:
        self._settings = settings
        self._repo = repo
        self._manifests: dict[str, ToolManifest] = {}
        self._impl_cache: dict[str, Any] = {}

    # --- lifecycle ---
    async def load(self) -> None:
        """Load persisted manifests; if none exist, run a first discovery."""
        self._settings.ensure_tool_library_importable()
        persisted = await self._repo.list()
        if persisted:
            self._manifests = {m.id: m for m in persisted}
            logger.info("Loaded %d tools from registry store", len(self._manifests))
        else:
            await self.refresh()

    async def refresh(self) -> dict[str, int]:
        """Re-scan the library and persist the result. Returns a summary."""
        self._settings.ensure_tool_library_importable()
        library_path = Path(self._settings.tool_library_path)
        manifests = await asyncio.to_thread(discover_tools, library_path)
        self._manifests = {m.id: m for m in manifests}
        self._impl_cache.clear()

        # Persist: replace whole collection.
        for existing in await self._repo.list():
            await self._repo.delete(existing.id)
        for m in manifests:
            await self._repo.add(m)

        categories = {m.category for m in manifests}
        logger.info("Registry refreshed: %d tools / %d categories",
                    len(manifests), len(categories))
        return {"tools": len(manifests), "categories": len(categories)}

    # --- lookup ---
    def all(self) -> list[ToolManifest]:
        return list(self._manifests.values())

    def get(self, tool_id: str) -> ToolManifest:
        m = self._manifests.get(tool_id)
        if not m:
            raise ToolNotFoundError(tool_id)
        return m

    def try_get(self, tool_id: str) -> ToolManifest | None:
        return self._manifests.get(tool_id)

    def by_category(self) -> dict[str, list[ToolManifest]]:
        out: dict[str, list[ToolManifest]] = {}
        for m in self._manifests.values():
            out.setdefault(m.category, []).append(m)
        return out

    def search(self, query: str) -> list[ToolManifest]:
        q = query.lower().strip()
        if not q:
            return self.all()
        return [
            m for m in self._manifests.values()
            if q in m.id.lower() or q in m.display_name.lower()
            or q in m.description.lower() or any(q in t for t in m.tags)
        ]

    # --- execution ---
    def _load_impl(self, manifest: ToolManifest) -> Any:
        """Import the tool module and instantiate its BaseTool subclass."""
        if manifest.id in self._impl_cache:
            return self._impl_cache[manifest.id]
        self._settings.ensure_tool_library_importable()
        module = importlib.import_module(manifest.impl_path)
        impl = None
        for obj in vars(module).values():
            if (
                isinstance(obj, type)
                and obj.__name__ != "BaseTool"
                and any(c.__name__ == "BaseTool" for c in obj.__mro__[1:])
            ):
                impl = obj()
                break
        if impl is None:
            raise ToolNotFoundError(f"No BaseTool subclass in {manifest.impl_path}")
        self._impl_cache[manifest.id] = impl
        return impl

    async def execute(self, tool_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run a tool by id with the given inputs. Always returns the tool's dict result."""
        manifest = self.get(tool_id)
        # Unwrap the LangChain {'kwargs': {...}} envelope if present.
        if list(input_data.keys()) == ["kwargs"] and isinstance(input_data["kwargs"], dict):
            input_data = input_data["kwargs"]
        try:
            impl = self._load_impl(manifest)
        except Exception as exc:
            logger.exception("Tool impl load failed: %s", tool_id)
            return {"status": "error", "message": f"Failed to load tool '{tool_id}': {exc}"}

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(_TOOL_EXECUTOR, impl.run, input_data)
        except Exception as exc:
            logger.exception("Tool execution raised: %s", tool_id)
            return {"status": "error", "message": str(exc)}
        if not isinstance(result, dict):
            result = {"status": "success", "data": result}
        return result

    @staticmethod
    def normalise_id(raw: str) -> str:
        """Normalise a tool/node id to the canonical registry id."""
        raw = raw.strip()
        if raw.startswith("tool."):
            raw = raw[len("tool."):]
        return re.sub(r"\s+", "_", raw)
