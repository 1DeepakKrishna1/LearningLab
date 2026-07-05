"""Action node handlers: send_email, send_whatsapp, api_call, file_write, generate_report."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...domain.execution import Execution
from ...domain.workflow import WorkflowNode
from ..context import ExecutionContext
from ..services import EngineServices
from .base import NodeResult, register_handler


class SendEmailHandler:
    """Delegates to the discovered Outlook send_email tool when available."""
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        cfg = ctx.interpolate(dict(node.data.config or {}))
        if services.registry.try_get("outlook.send_email") is None:
            return NodeResult.fail("send_email tool not available in the registry.")
        result = await services.registry.execute("outlook.send_email", cfg)
        if result.get("status") == "error":
            return NodeResult.fail(result.get("message", "send_email failed"))
        return NodeResult.ok(result)


class SendWhatsAppHandler:
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        cfg = ctx.interpolate(dict(node.data.config or {}))
        to, body = cfg.get("to"), cfg.get("message", cfg.get("body", ""))
        if not to:
            return NodeResult.fail("'to' is required for send_whatsapp.")
        if not services.messaging:
            return NodeResult.fail("No messaging provider configured.")
        res = await services.messaging.send(to, body)
        return NodeResult.ok({"sent": True, "provider_result": res})


class ApiCallHandler:
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        import httpx
        cfg = ctx.interpolate(dict(node.data.config or {}))
        method = (cfg.get("method") or "GET").upper()
        url = cfg.get("url")
        if not url:
            return NodeResult.fail("'url' is required for api_call.")
        async with httpx.AsyncClient(timeout=cfg.get("timeout", 30)) as client:
            resp = await client.request(
                method, url,
                headers=cfg.get("headers"),
                params=cfg.get("params"),
                json=cfg.get("json"),
                data=cfg.get("data"),
            )
        body: Any
        try:
            body = resp.json()
        except Exception:  # noqa: BLE001
            body = resp.text
        return NodeResult.ok({"status_code": resp.status_code, "body": body})


class FileWriteHandler:
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        cfg = ctx.interpolate(dict(node.data.config or {}))
        path = cfg.get("path")
        if not path:
            return NodeResult.fail("'path' is required for file_write.")
        content = cfg.get("content", "")
        if not isinstance(content, str):
            content = json.dumps(content, indent=2, ensure_ascii=False)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return NodeResult.ok({"path": str(p), "bytes": len(content.encode("utf-8"))})


class GenerateReportHandler:
    """Render a simple markdown/JSON report from inputs and write it to disk."""
    async def execute(self, node: WorkflowNode, ctx: ExecutionContext,
                      services: EngineServices, execution: Execution) -> NodeResult:
        cfg = ctx.interpolate(dict(node.data.config or {}))
        title = cfg.get("title", "Report")
        sections = cfg.get("sections", [])
        fmt = cfg.get("format", "markdown")
        if fmt == "json":
            content = json.dumps({"title": title, "sections": sections,
                                  "context": ctx.snapshot()}, indent=2, ensure_ascii=False)
        else:
            lines = [f"# {title}", ""]
            for s in sections if isinstance(sections, list) else [sections]:
                if isinstance(s, dict):
                    lines.append(f"## {s.get('heading', '')}")
                    lines.append(str(s.get("body", "")))
                else:
                    lines.append(str(s))
                lines.append("")
            content = "\n".join(lines)
        out: dict[str, Any] = {"title": title, "format": fmt, "content": content}
        if cfg.get("path"):
            p = Path(cfg["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            out["path"] = str(p)
        return NodeResult.ok(out)


register_handler("action.send_email", SendEmailHandler())
register_handler("action.send_whatsapp", SendWhatsAppHandler())
register_handler("action.api_call", ApiCallHandler())
register_handler("action.file_write", FileWriteHandler())
register_handler("action.generate_report", GenerateReportHandler())
