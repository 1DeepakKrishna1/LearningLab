"""
Pattern 10: Model Context Protocol (MCP)
==========================================
Concept: Implements the core MCP design pattern — a structured registry of
Resources, Tools, and Prompts. A context builder assembles a context window
respecting a token budget, with explicit priority ordering and overflow handling.

Components:
  - MCPRegistry   : catalogue of resources, tools, and prompt templates
  - ContextBuilder: assembles context slots with budget allocation
  - MCPClient     : routes requests through the assembled context

Graph:  START → resolve_context_needs → fetch_resources → allocate_budget
              → assemble_context → call_llm → log_context_usage → END

Demo:   Customer support ticket: "I can't access my account after the recent update."
        Context includes: system policy, user account info (resource), KB articles
        (resource), available actions (tools), and the support prompt template.
"""
from __future__ import annotations

import textwrap
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE, MODEL_SMALL


# -------------------------------------------------------------------- MCP Registry

@dataclass
class MCPResource:
    """A named data resource that can be fetched by the context builder."""
    name: str
    description: str
    fetch: Callable[..., str]
    priority: int = 5          # 1 (highest) – 10 (lowest)
    estimated_tokens: int = 200


@dataclass
class MCPTool:
    """A callable tool with a JSON schema for the LLM."""
    name: str
    description: str
    schema: Dict[str, Any]
    handler: Callable[..., str]
    priority: int = 5


@dataclass
class MCPPromptTemplate:
    """A reusable prompt template stored in the registry."""
    name: str
    template: str
    variables: List[str]


class MCPRegistry:
    """Central registry of all MCP resources, tools, and prompt templates."""

    def __init__(self) -> None:
        self._resources: Dict[str, MCPResource] = {}
        self._tools: Dict[str, MCPTool] = {}
        self._prompts: Dict[str, MCPPromptTemplate] = {}

    def register_resource(self, res: MCPResource) -> None:
        self._resources[res.name] = res

    def register_tool(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool

    def register_prompt(self, prompt: MCPPromptTemplate) -> None:
        self._prompts[prompt.name] = prompt

    def get_resource(self, name: str) -> Optional[MCPResource]:
        return self._resources.get(name)

    def get_tool(self, name: str) -> Optional[MCPTool]:
        return self._tools.get(name)

    def get_prompt(self, name: str) -> Optional[MCPPromptTemplate]:
        return self._prompts.get(name)

    def list_resources(self) -> List[str]:
        return list(self._resources.keys())

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())


# -------------------------------------------------------------------- Mock data / handlers

def _fetch_system_policy() -> str:
    return textwrap.dedent("""\
        SYSTEM POLICY — Customer Support:
        1. Never share passwords or internal IDs with users.
        2. Account lockouts require identity verification before unlock.
        3. Escalate billing issues to Tier-2 within 24 hours.
        4. All actions must be logged in the support ticket system.
    """)


def _fetch_user_account(user_id: str = "u-2947") -> str:
    return textwrap.dedent(f"""\
        USER ACCOUNT ({user_id}):
        - Name: Jordan Smith
        - Email: jordan.smith@example.com
        - Account status: LOCKED (auto-locked after 3 failed attempts, 2025-03-14)
        - Subscription: Pro tier, active
        - Last login: 2025-03-13 from 192.168.0.1
        - MFA enabled: Yes (TOTP)
    """)


def _fetch_kb_articles(query: str = "account locked") -> str:
    return textwrap.dedent("""\
        KB-1042: Account Lockout Policy
          Accounts are locked after 3 consecutive failed login attempts.
          Users can self-service unlock via the 'Forgot Password' flow.
          Admins can manually unlock via Settings > User Management.

        KB-2018: Recent Update — Auth Changes (v3.7.0)
          The v3.7.0 update introduced stricter session validation.
          Known issue: TOTP codes from some authenticator apps may have
          clock-skew issues. Workaround: resync device time.
    """)


def _tool_unlock_account(user_id: str) -> str:
    return f"Account {user_id} has been unlocked. Email sent to user."


def _tool_reset_mfa(user_id: str) -> str:
    return f"MFA reset initiated for {user_id}. User will receive instructions."


# -------------------------------------------------------------------- State & Pattern

class MCPState(TypedDict):
    request: str
    context_slots: Dict[str, str]
    context_budget_tokens: int
    allocated_tokens: Dict[str, int]
    active_context: str
    response: str
    context_version: int
    tools_listed: List[str]
    usage_log: List[Dict[str, Any]]


class PatternModelContextProtocol(BasePattern):
    PATTERN_NUMBER = 10
    PATTERN_NAME = "Model Context Protocol"
    DESCRIPTION = (
        "Structured context registry (resources, tools, prompts) with budget allocation."
    )

    def __init__(self, llm_client: Any) -> None:
        super().__init__(llm_client)
        self.registry = self._build_registry()

    def _build_registry(self) -> MCPRegistry:
        reg = MCPRegistry()

        reg.register_resource(MCPResource(
            name="system_policy",
            description="Support team operating policies",
            fetch=_fetch_system_policy,
            priority=1,
            estimated_tokens=120,
        ))
        reg.register_resource(MCPResource(
            name="user_account",
            description="Current user's account information",
            fetch=_fetch_user_account,
            priority=2,
            estimated_tokens=150,
        ))
        reg.register_resource(MCPResource(
            name="kb_articles",
            description="Knowledge base articles relevant to the query",
            fetch=_fetch_kb_articles,
            priority=3,
            estimated_tokens=250,
        ))
        reg.register_tool(MCPTool(
            name="unlock_account",
            description="Unlock a user account",
            schema={"type": "function", "function": {"name": "unlock_account", "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}}}}},
            handler=_tool_unlock_account,
            priority=2,
        ))
        reg.register_tool(MCPTool(
            name="reset_mfa",
            description="Trigger an MFA reset for a user",
            schema={"type": "function", "function": {"name": "reset_mfa", "parameters": {"type": "object", "properties": {"user_id": {"type": "string"}}}}},
            handler=_tool_reset_mfa,
            priority=3,
        ))
        reg.register_prompt(MCPPromptTemplate(
            name="support_agent",
            template=(
                "You are a customer support specialist for a SaaS platform. "
                "You have access to the following information and tools.\n\n"
                "{context}\n\n"
                "Customer request: {request}\n\n"
                "Provide a helpful, empathetic, and accurate response. "
                "If you need to take an action, indicate which tool to use."
            ),
            variables=["context", "request"],
        ))
        return reg

    # ------------------------------------------------------------------ nodes

    def _resolve_context_needs(self, state: MCPState) -> dict:
        """Determine which resources are relevant to this request."""
        needed = list(self.registry.list_resources())
        return {
            "context_slots": {r: "" for r in needed},
            "tools_listed": list(self.registry.list_tools()),
        }

    def _fetch_resources(self, state: MCPState) -> dict:
        """Fetch content for each resource slot."""
        filled: Dict[str, str] = {}
        for name in state["context_slots"]:
            resource = self.registry.get_resource(name)
            if resource:
                filled[name] = resource.fetch()
        return {"context_slots": filled}

    def _allocate_budget(self, state: MCPState) -> dict:
        """Allocate token budget across context slots by priority."""
        budget = state["context_budget_tokens"]
        resources_sorted = sorted(
            [self.registry.get_resource(n) for n in state["context_slots"] if self.registry.get_resource(n)],
            key=lambda r: r.priority,
        )
        allocation: Dict[str, int] = {}
        remaining = budget
        for res in resources_sorted:
            alloc = min(res.estimated_tokens, remaining)
            allocation[res.name] = alloc
            remaining -= alloc
            if remaining <= 0:
                break
        return {"allocated_tokens": allocation}

    def _assemble_context(self, state: MCPState) -> dict:
        """Build the final context string, truncating to allocated token budgets."""
        parts: List[str] = []
        for slot_name, content in state["context_slots"].items():
            token_budget = state["allocated_tokens"].get(slot_name, 100)
            # Rough truncation: ~4 chars per token
            char_limit = token_budget * 4
            truncated = content[:char_limit] + ("…" if len(content) > char_limit else "")
            parts.append(f"[{slot_name.upper()}]\n{truncated}")

        # List available tools
        tool_descriptions = "\n".join(
            f"- {t}: {self.registry.get_tool(t).description}"
            for t in state["tools_listed"]
            if self.registry.get_tool(t)
        )
        if tool_descriptions:
            parts.append(f"[AVAILABLE TOOLS]\n{tool_descriptions}")

        active_context = "\n\n".join(parts)
        return {
            "active_context": active_context,
            "context_version": state["context_version"] + 1,
        }

    def _call_llm(self, state: MCPState) -> dict:
        """Fill the prompt template and call the LLM."""
        template = self.registry.get_prompt("support_agent")
        if template:
            prompt = template.template.format(
                context=state["active_context"],
                request=state["request"],
            )
        else:
            prompt = f"Context:\n{state['active_context']}\n\nRequest: {state['request']}"

        response = self.llm.simple_prompt(prompt, model=MODEL_LARGE, max_tokens=600)
        return {"response": response}

    def _log_context_usage(self, state: MCPState) -> dict:
        total_allocated = sum(state["allocated_tokens"].values())
        log_entry = {
            "context_version": state["context_version"],
            "slots_filled": len(state["context_slots"]),
            "tools_available": len(state["tools_listed"]),
            "tokens_allocated": total_allocated,
            "budget": state["context_budget_tokens"],
            "utilization_pct": round(total_allocated / state["context_budget_tokens"] * 100, 1),
        }
        return {"usage_log": [log_entry]}

    # --------------------------------------------------------------- graph

    def build_graph(self) -> StateGraph:
        graph = StateGraph(MCPState)

        graph.add_node("resolve_context_needs", self._resolve_context_needs)
        graph.add_node("fetch_resources", self._fetch_resources)
        graph.add_node("allocate_budget", self._allocate_budget)
        graph.add_node("assemble_context", self._assemble_context)
        graph.add_node("call_llm", self._call_llm)
        graph.add_node("log_context_usage", self._log_context_usage)

        graph.add_edge(START, "resolve_context_needs")
        graph.add_edge("resolve_context_needs", "fetch_resources")
        graph.add_edge("fetch_resources", "allocate_budget")
        graph.add_edge("allocate_budget", "assemble_context")
        graph.add_edge("assemble_context", "call_llm")
        graph.add_edge("call_llm", "log_context_usage")
        graph.add_edge("log_context_usage", END)

        return graph.compile()

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            initial: MCPState = {
                "request": input_data,
                "context_slots": {},
                "context_budget_tokens": kwargs.get("token_budget", 800),
                "allocated_tokens": {},
                "active_context": "",
                "response": "",
                "context_version": 0,
                "tools_listed": [],
                "usage_log": [],
            }
            final, elapsed_ms = self._timed_run(app.invoke, initial)
            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final["response"],
                elapsed_ms=elapsed_ms,
                steps=final["usage_log"],
                metadata={
                    "resources_fetched": list(final["context_slots"].keys()),
                    "tools_registered": final["tools_listed"],
                    "context_version": final["context_version"],
                    "token_utilization": final["usage_log"][-1].get("utilization_pct") if final["usage_log"] else 0,
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
