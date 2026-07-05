"""
Pattern 10 – Model Context Protocol (MCP)
==========================================
MCP (Anthropic's Model Context Protocol) standardises how AI models
discover and interact with external tools, resources, and prompts
via a JSON-RPC 2.0-style message format.

This module simulates the key MCP architectural concepts:
  • MCPServer  – registers and exposes tools and resources
  • MCPClient  – discovers capabilities and invokes them
  • MCPAgent   – an LLM agent that uses MCPClient to fulfil requests

MCP concepts demonstrated:
  tools/list     → discover available tools
  tools/call     → invoke a tool by name with arguments
  resources/list → discover available data resources
  resources/read → read a resource by URI
  prompts/list   → discover reusable prompt templates
  prompts/get    → retrieve a filled prompt template

(The actual @modelcontextprotocol/sdk is not required; this shows
 the pattern and message format for educational purposes.)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from llm_client import GroqClient, Message
from patterns.base import BasePattern

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MCP message types  (JSON-RPC 2.0 style)
# ---------------------------------------------------------------------------


@dataclass
class MCPRequest:
    method: str
    params: dict[str, Any] = field(default_factory=dict)
    id: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": self.id, "method": self.method, "params": self.params}


@dataclass
class MCPResponse:
    id: int
    result: Any = None
    error: Optional[dict[str, Any]] = None

    @property
    def ok(self) -> bool:
        return self.error is None


# ---------------------------------------------------------------------------
# MCP tool / resource / prompt schemas
# ---------------------------------------------------------------------------


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., str]


@dataclass
class MCPResource:
    uri: str
    name: str
    description: str
    mime_type: str
    content: str  # inline content for demo


@dataclass
class MCPPrompt:
    name: str
    description: str
    arguments: list[dict[str, str]]  # [{"name": ..., "description": ..., "required": ...}]
    template: str  # uses {argument_name} placeholders


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------


class MCPServer:
    """
    Simulated MCP server.

    Registers tools, resources, and prompt templates, and handles
    JSON-RPC-style requests from the MCPClient.
    """

    SERVER_INFO = {"name": "demo-mcp-server", "version": "1.0.0"}

    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}
        self._resources: dict[str, MCPResource] = {}
        self._prompts: dict[str, MCPPrompt] = {}
        self._req_counter = 0

    # ── Registration ─────────────────────────────────────────────────

    def register_tool(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool
        logger.debug("MCP tool registered: %s", tool.name)

    def register_resource(self, resource: MCPResource) -> None:
        self._resources[resource.uri] = resource

    def register_prompt(self, prompt: MCPPrompt) -> None:
        self._prompts[prompt.name] = prompt

    # ── Request handler ───────────────────────────────────────────────

    def handle(self, request: MCPRequest) -> MCPResponse:
        """Dispatch a JSON-RPC request and return the response."""
        method = request.method
        params = request.params

        handlers = {
            "initialize":       self._handle_initialize,
            "tools/list":       self._handle_tools_list,
            "tools/call":       self._handle_tools_call,
            "resources/list":   self._handle_resources_list,
            "resources/read":   self._handle_resources_read,
            "prompts/list":     self._handle_prompts_list,
            "prompts/get":      self._handle_prompts_get,
        }
        fn = handlers.get(method)
        if fn is None:
            return MCPResponse(
                id=request.id,
                error={"code": -32601, "message": f"Method not found: {method}"},
            )
        try:
            result = fn(params)
            return MCPResponse(id=request.id, result=result)
        except Exception as exc:
            return MCPResponse(
                id=request.id,
                error={"code": -32603, "message": str(exc)},
            )

    def _handle_initialize(self, _: dict) -> dict:
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": self.SERVER_INFO,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
        }

    def _handle_tools_list(self, _: dict) -> dict:
        return {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.input_schema,
                }
                for t in self._tools.values()
            ]
        }

    def _handle_tools_call(self, params: dict) -> dict:
        name = params.get("name")
        arguments = params.get("arguments", {})
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        result = tool.handler(**arguments)
        return {"content": [{"type": "text", "text": result}], "isError": False}

    def _handle_resources_list(self, _: dict) -> dict:
        return {
            "resources": [
                {
                    "uri": r.uri,
                    "name": r.name,
                    "description": r.description,
                    "mimeType": r.mime_type,
                }
                for r in self._resources.values()
            ]
        }

    def _handle_resources_read(self, params: dict) -> dict:
        uri = params.get("uri")
        resource = self._resources.get(uri)
        if not resource:
            raise ValueError(f"Resource not found: {uri}")
        return {
            "contents": [
                {"uri": resource.uri, "mimeType": resource.mime_type, "text": resource.content}
            ]
        }

    def _handle_prompts_list(self, _: dict) -> dict:
        return {
            "prompts": [
                {"name": p.name, "description": p.description, "arguments": p.arguments}
                for p in self._prompts.values()
            ]
        }

    def _handle_prompts_get(self, params: dict) -> dict:
        name = params.get("name")
        arguments = params.get("arguments", {})
        prompt = self._prompts.get(name)
        if not prompt:
            raise ValueError(f"Unknown prompt: {name}")
        filled = prompt.template.format(**arguments)
        return {
            "description": prompt.description,
            "messages": [{"role": "user", "content": {"type": "text", "text": filled}}],
        }


# ---------------------------------------------------------------------------
# MCP Client
# ---------------------------------------------------------------------------


class MCPClient:
    """Thin client that wraps MCPServer.handle() with a clean interface."""

    def __init__(self, server: MCPServer) -> None:
        self._server = server
        self._req_id = 0
        # Initialise the connection
        resp = self._call("initialize", {"clientInfo": {"name": "mcp-agent", "version": "1.0"}})
        logger.debug("MCP initialised: %s", resp.result)

    def _call(self, method: str, params: dict[str, Any] | None = None) -> MCPResponse:
        self._req_id += 1
        return self._server.handle(MCPRequest(method=method, params=params or {}, id=self._req_id))

    def list_tools(self) -> list[dict]:
        resp = self._call("tools/list")
        return resp.result.get("tools", []) if resp.ok else []

    def call_tool(self, name: str, arguments: dict) -> str:
        resp = self._call("tools/call", {"name": name, "arguments": arguments})
        if not resp.ok:
            return f"Tool error: {resp.error}"
        contents = resp.result.get("content", [])
        return "\n".join(c.get("text", "") for c in contents if c.get("type") == "text")

    def list_resources(self) -> list[dict]:
        resp = self._call("resources/list")
        return resp.result.get("resources", []) if resp.ok else []

    def read_resource(self, uri: str) -> str:
        resp = self._call("resources/read", {"uri": uri})
        if not resp.ok:
            return f"Resource error: {resp.error}"
        contents = resp.result.get("contents", [])
        return "\n".join(c.get("text", "") for c in contents)

    def list_prompts(self) -> list[dict]:
        resp = self._call("prompts/list")
        return resp.result.get("prompts", []) if resp.ok else []

    def get_prompt(self, name: str, arguments: dict) -> str:
        resp = self._call("prompts/get", {"name": name, "arguments": arguments})
        if not resp.ok:
            return f"Prompt error: {resp.error}"
        messages = resp.result.get("messages", [])
        return "\n".join(
            m["content"]["text"] for m in messages if m.get("content", {}).get("type") == "text"
        )


# ---------------------------------------------------------------------------
# Demo server setup
# ---------------------------------------------------------------------------


def _build_demo_server() -> MCPServer:
    """Construct an MCP server populated with demo tools, resources, prompts."""
    import math
    from datetime import date

    server = MCPServer()

    # Tools
    server.register_tool(MCPTool(
        name="calculate",
        description="Evaluate a safe arithmetic expression.",
        input_schema={
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
        handler=lambda expression: str(
            eval(expression, {"__builtins__": {}}, {"sqrt": math.sqrt, "pi": math.pi})  # noqa: S307
        ),
    ))
    server.register_tool(MCPTool(
        name="get_date",
        description="Return today's date.",
        input_schema={"type": "object", "properties": {}, "required": []},
        handler=lambda: date.today().isoformat(),
    ))

    # Resources
    server.register_resource(MCPResource(
        uri="company://products/overview",
        name="Product Overview",
        description="High-level overview of the company's AI products.",
        mime_type="text/plain",
        content=(
            "Our AI product suite:\n"
            "1. CodeAssist – AI pair programmer for VS Code\n"
            "2. DataSense   – Natural language querying for databases\n"
            "3. DocuBot     – Automated document analysis and summarisation\n"
            "All products use LLMs under the hood and are SOC-2 compliant."
        ),
    ))

    # Prompts
    server.register_prompt(MCPPrompt(
        name="product_faq",
        description="Generate an FAQ for a given product.",
        arguments=[
            {"name": "product_name", "description": "Name of the product", "required": "true"},
            {"name": "audience", "description": "Target audience", "required": "false"},
        ],
        template=(
            "Generate 5 frequently asked questions and answers for '{product_name}' "
            "targeting '{audience}'. Be concise and informative."
        ),
    ))

    return server


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


class ModelContextProtocolPattern(BasePattern):
    """
    Demonstrates the Model Context Protocol (MCP) architecture.

    An LLM agent uses an MCPClient to discover and invoke tools,
    read resources, and fill prompt templates — mirroring how Claude
    integrates with MCP servers in production.
    """

    name = "10 · Model Context Protocol (MCP)"

    async def run(self, query: str = "What products does our company offer and what is today's date?") -> dict[str, Any]:  # type: ignore[override]
        self.print_header()

        # ── Bootstrap MCP infrastructure ─────────────────────────────
        server = _build_demo_server()
        mcp = MCPClient(server)

        # ── Step 1: Capability discovery ──────────────────────────────
        tools = mcp.list_tools()
        resources = mcp.list_resources()
        prompts = mcp.list_prompts()

        capabilities_summary = (
            f"Tools ({len(tools)}):     " + ", ".join(t["name"] for t in tools) + "\n"
            f"Resources ({len(resources)}): " + ", ".join(r["name"] for r in resources) + "\n"
            f"Prompts ({len(prompts)}):   " + ", ".join(p["name"] for p in prompts)
        )
        self.print_step("Step 1 › Capability Discovery", capabilities_summary)

        # ── Step 2: Read a relevant resource ─────────────────────────
        product_info = mcp.read_resource("company://products/overview")
        self.print_step("Step 2 › Resource Read (company://products/overview)", product_info)

        # ── Step 3: Invoke a tool ─────────────────────────────────────
        today = mcp.call_tool("get_date", {})
        self.print_step("Step 3 › Tool Call (get_date)", today)

        # ── Step 4: Fill a prompt template ────────────────────────────
        faq_prompt = mcp.get_prompt(
            "product_faq",
            {"product_name": "CodeAssist", "audience": "software developers"},
        )
        self.print_step("Step 4 › Prompt Template (product_faq)", faq_prompt)

        # ── Step 5: LLM synthesis using MCP-gathered context ─────────
        context_block = (
            f"Company products:\n{product_info}\n\n"
            f"Today's date: {today}\n\n"
            f"User query: {query}"
        )
        answer = await self.client.complete_text(
            context_block,
            system=(
                "You are a helpful assistant. Answer the user's query using the "
                "provided context. Cite specific product names and today's date where relevant."
            ),
            max_tokens=400,
        )
        self.print_step("Step 5 › LLM Response (using MCP context)", answer)

        self.print_result(answer)
        return {
            "query": query,
            "tools_discovered": [t["name"] for t in tools],
            "resources_discovered": [r["uri"] for r in resources],
            "answer": answer,
        }
