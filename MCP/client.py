#!/usr/bin/env python3
"""
MCP Client using Groq as the LLM provider.

Usage:
    python client.py

Environment:
    GROQ_API_KEY — required
    GROQ_MODEL   — optional override (default: llama-3.3-70b-versatile)
"""

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # loads .env from the current working directory (or any parent)

import groq
import openai
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------
_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    raise EnvironmentError("GROQ_API_KEY is not set in .env")

_llm = openai.OpenAI(
    api_key=_api_key,
    base_url="https://api.groq.com/openai/v1",
)
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SERVER_SCRIPT = str(Path(__file__).parent / "server.py")

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a calculator and a stock-price "
    "lookup tool. Use them whenever the user's request requires arithmetic or "
    "stock price information. When given a multi-step plan, execute ONE tool call "
    "at a time. ALWAYS wait for the actual result of each tool call before making "
    "the next one. NEVER guess, estimate, or hallucinate values - always use the "
    "exact numbers returned by previous tool calls as inputs to subsequent tools. "
    "Summarise all results clearly at the end."
)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
class MCPClient:
    """Manages the MCP session and the LLM agentic loop."""

    def __init__(self) -> None:
        self._exit_stack = AsyncExitStack()
        self._session: ClientSession | None = None
        self._tools: list[dict] = []      # OpenAI-format tool definitions

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def connect(self, server_script: str) -> None:
        """Start the MCP server subprocess and initialise the session."""
        params = StdioServerParameters(
            command=sys.executable,   # same Python interpreter as the client
            args=[server_script],
        )
        transport = await self._exit_stack.enter_async_context(
            stdio_client(params)
        )
        read, write = transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self._session.initialize()

        # Discover tools and convert to OpenAI function-calling schema
        tools_resp = await self._session.list_tools()
        self._tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema,   # MCP uses JSON Schema — same format
                },
            }
            for t in tools_resp.tools
        ]
        names = [t["function"]["name"] for t in self._tools]
        print(f"[MCP] Connected. Tools available: {names}")

    async def close(self) -> None:
        await self._exit_stack.aclose()

    # ------------------------------------------------------------------
    # Agentic execution loop
    # ------------------------------------------------------------------
    async def execute(self, user_input: str) -> str:
        """
        Run the agentic loop for the given user input.

        The LLM may request tool calls zero or more times before producing a
        final text response.  Each tool call is forwarded to the MCP server;
        results are fed back until finish_reason == 'stop'.
        """
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_input},
        ]

        while True:
            response = _llm.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=self._tools if self._tools else openai.NOT_GIVEN,
                tool_choice="auto",
                parallel_tool_calls=False,
            )

            choice = response.choices[0]
            message = choice.message
            finish_reason = choice.finish_reason

            # No tool calls → return final text answer
            if finish_reason == "stop" or not message.tool_calls:
                return (message.content or "").strip()

            # Append assistant turn with tool_calls
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,   # may be None
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,  # JSON string
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
            )

            # Execute every tool call via MCP and collect results
            for tc in message.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                print(f"  → {fn_name}({json.dumps(fn_args, ensure_ascii=False)})")
                mcp_result = await self._session.call_tool(fn_name, fn_args)
                result_text = (
                    mcp_result.content[0].text if mcp_result.content else "(no output)"
                )
                print(f"  ← {result_text}")

                # Feed the tool result back as a "tool" role message
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_text,
                    }
                )


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------
async def main() -> None:
    client = MCPClient()
    try:
        await client.connect(SERVER_SCRIPT)
        print(
            f"\nMCP Client ready. (Provider: groq · Model: {MODEL})\n"
            "Type a question, a calculation, or a multi-step plan.\n"
            "Type 'quit' or press Ctrl-C to exit.\n"
        )

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_input:
                continue
            if user_input.lower() in {"quit", "exit", "q"}:
                break

            print("Thinking...\n")
            try:
                answer = await client.execute(user_input)
            except Exception as exc:  # noqa: BLE001
                print(f"[Error] {exc}\n")
                continue

            print(f"Assistant: {answer}\n")
    finally:
        await client.close()
        print("Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
