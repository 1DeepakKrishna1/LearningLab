"""An OpenClaw agent — a LangChain tool-calling agent backed by registry tools.

This is the concrete runtime for the platform's agent nodes. It degrades
gracefully: if LangChain / an LLM provider is not configured, `run` returns a
structured error instead of raising, so the rest of the platform keeps working.
"""
from __future__ import annotations

import asyncio
from typing import Any

from ..domain.agent import Agent
from ..logging_setup import get_logger
from ..registry.openclaw_tool import build_openclaw_tools
from ..registry.tool_registry import ToolRegistry
from .prompts import system_prompt_for

logger = get_logger("agent.openclaw")


def _resolve_llm(agent: Agent, default_provider: str, default_model: str) -> Any:
    """Build a LangChain chat model via the unified resolver (Groq + library providers)."""
    from ..llm import resolve_chat_model

    return resolve_chat_model(
        provider=agent.provider or default_provider,
        model=agent.model or default_model,
        temperature=agent.temperature,
    )


class OpenClawAgent:
    """Wraps a persisted :class:`Agent` definition into a runnable agent."""

    def __init__(self, agent: Agent, registry: ToolRegistry,
                 default_provider: str, default_model: str) -> None:
        self.agent = agent
        self._registry = registry
        self._default_provider = default_provider
        self._default_model = default_model

    def _allowed_tool_ids(self) -> list[str]:
        allow = self.agent.limits.tool_allow_list or self.agent.tools
        return [self._registry.normalise_id(t) for t in allow]

    async def run(self, task: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the agent against a task. Returns {status, output, steps, error}."""
        context = context or {}
        system_prompt = system_prompt_for(self.agent.role, self.agent.system_prompt)

        try:
            llm = _resolve_llm(self.agent, self._default_provider, self._default_model)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM unavailable for agent %s: %s", self.agent.name, exc)
            return {"status": "error", "output": None,
                    "error": f"LLM provider not configured: {exc}", "steps": []}

        tools = build_openclaw_tools(self._registry, self._allowed_tool_ids())

        try:
            return await asyncio.wait_for(
                self._run_agent(llm, tools, system_prompt, task, context),
                timeout=self.agent.limits.timeout_seconds,
            )
        except asyncio.TimeoutError:
            return {"status": "error", "output": None,
                    "error": f"Agent timed out after {self.agent.limits.timeout_seconds}s",
                    "steps": []}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Agent %s failed", self.agent.name)
            return {"status": "error", "output": None, "error": str(exc), "steps": []}

    async def _run_agent(self, llm: Any, tools: list[Any], system_prompt: str,
                         task: str, context: dict[str, Any]) -> dict[str, Any]:
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        ctx_str = "\n".join(f"{k}: {v}" for k, v in context.items()) if context else "(none)"
        human = f"Upstream context:\n{ctx_str}\n\nTask:\n{task}"

        if not tools:
            # No tools → a single LLM completion.
            messages = [("system", system_prompt), ("human", human)]
            resp = await llm.ainvoke(messages)
            text = getattr(resp, "content", str(resp))
            return {"status": "success", "output": text, "steps": []}

        from langchain.agents import AgentExecutor, create_tool_calling_agent

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])
        agent = create_tool_calling_agent(llm, tools, prompt)
        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            max_iterations=self.agent.limits.max_iterations,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            verbose=False,
        )
        result = await executor.ainvoke({"input": human})
        steps = [
            {"tool": getattr(a, "tool", "?"), "input": getattr(a, "tool_input", {}),
             "observation": str(o)[:2000]}
            for a, o in result.get("intermediate_steps", [])
        ]
        return {"status": "success", "output": result.get("output", ""), "steps": steps}
