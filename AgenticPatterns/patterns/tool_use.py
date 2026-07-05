"""
Pattern 5 – Tool Use
======================
The LLM is given a set of callable tools (functions).  When the LLM
decides a tool is needed, it emits a structured ``tool_call``; the
agent executes the function locally and sends the result back.  This
loop continues until the LLM produces a final text answer.

Tools available in this demo:
  • calculator        – evaluate safe arithmetic expressions
  • get_current_date  – return today's date
  • count_words       – count words in a text string
  • unit_converter    – convert between common units
"""

from __future__ import annotations

import json
import logging
import math
import operator
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable

from llm_client import GroqClient, Message, ToolCall
from patterns.base import BasePattern

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _calculator(expression: str) -> str:
    """Evaluate a safe arithmetic expression and return the result."""
    # Restrict to safe operations only (no builtins, no imports)
    allowed_names: dict[str, Any] = {
        "abs": abs, "round": round,
        "sqrt": math.sqrt, "pow": math.pow,
        "pi": math.pi, "e": math.e,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10,
        "floor": math.floor, "ceil": math.ceil,
    }
    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)  # noqa: S307
        return str(result)
    except Exception as exc:
        return f"Error evaluating expression: {exc}"


def _get_current_date() -> str:
    return date.today().isoformat()


def _count_words(text: str) -> str:
    count = len(text.split())
    return f"{count} words"


def _unit_converter(value: float, from_unit: str, to_unit: str) -> str:
    conversions: dict[tuple[str, str], float] = {
        ("km", "miles"): 0.621371,
        ("miles", "km"): 1.60934,
        ("kg", "lbs"): 2.20462,
        ("lbs", "kg"): 0.453592,
        ("celsius", "fahrenheit"): None,  # handled specially
        ("fahrenheit", "celsius"): None,
        ("meters", "feet"): 3.28084,
        ("feet", "meters"): 0.3048,
    }
    key = (from_unit.lower(), to_unit.lower())
    if key == ("celsius", "fahrenheit"):
        return f"{value * 9/5 + 32:.4g} fahrenheit"
    if key == ("fahrenheit", "celsius"):
        return f"{(value - 32) * 5/9:.4g} celsius"
    factor = conversions.get(key)
    if factor is None:
        return f"Unsupported conversion: {from_unit} → {to_unit}"
    return f"{value * factor:.6g} {to_unit}"


_TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "calculator": _calculator,
    "get_current_date": _get_current_date,
    "count_words": _count_words,
    "unit_converter": _unit_converter,
}

# ---------------------------------------------------------------------------
# Groq tool schema definitions
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": (
                "Evaluate a mathematical expression. Supports +, -, *, /, **, sqrt, "
                "sin, cos, tan, log, log10, pi, e, floor, ceil, round, abs, pow."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The arithmetic expression to evaluate, e.g. '2 ** 10 + sqrt(144)'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Return today's date in ISO 8601 format (YYYY-MM-DD).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_words",
            "description": "Count the number of words in the provided text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to count words in."}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "unit_converter",
            "description": (
                "Convert a value between units. "
                "Supported conversions: km↔miles, kg↔lbs, celsius↔fahrenheit, meters↔feet."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "The numeric value to convert."},
                    "from_unit": {"type": "string", "description": "Source unit."},
                    "to_unit": {"type": "string", "description": "Target unit."},
                },
                "required": ["value", "from_unit", "to_unit"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict[str, Any]
    result: str


@dataclass
class ToolUseResult:
    query: str
    tool_calls_made: list[ToolCallRecord] = field(default_factory=list)
    final_answer: str = ""


class ToolUsePattern(BasePattern):
    """
    Demonstrates native function/tool calling with Groq.

    The agent autonomously decides which tools to invoke, executes
    them locally, and feeds results back to the LLM until it produces
    a final natural-language answer.
    """

    name = "5 · Tool Use"

    def _execute_tool(self, tool_call: ToolCall) -> str:
        """Dispatch a ToolCall to the corresponding local function."""
        fn = _TOOL_REGISTRY.get(tool_call.name)
        if fn is None:
            return f"Unknown tool: {tool_call.name}"
        try:
            return fn(**tool_call.arguments)
        except TypeError as exc:
            return f"Tool argument error: {exc}"

    async def run(  # type: ignore[override]
        self,
        query: str = (
            "What is the square root of 1764 plus 42 squared? "
            "Also convert that result from km to miles. "
            "Finally, tell me today's date."
        ),
        max_tool_rounds: int = 8,
    ) -> ToolUseResult:
        self.print_header()
        print(f"Query: {query}\n")

        result = ToolUseResult(query=query)
        messages: list[Message] = [
            Message(
                role="system",
                content=(
                    "You are a helpful assistant with access to tools. "
                    "Use the tools when needed to answer the user's question accurately."
                ),
            ),
            Message(role="user", content=query),
        ]

        for round_num in range(1, max_tool_rounds + 1):
            response = await self.client.complete(
                messages,
                tools=TOOL_SCHEMAS,
                max_tokens=512,
            )

            if not response.has_tool_calls:
                # LLM produced a final answer
                result.final_answer = response.content
                self.print_step("Final Answer", response.content)
                break

            # Append the assistant message with its raw tool_calls (required by API)
            messages.append(response.as_assistant_message())

            # Execute each tool call and append the tool result messages
            for tc in response.tool_calls:
                tool_result = self._execute_tool(tc)
                record = ToolCallRecord(
                    name=tc.name,
                    arguments=tc.arguments,
                    result=tool_result,
                )
                result.tool_calls_made.append(record)
                self.print_step(
                    f"Round {round_num} › Tool: {tc.name}",
                    f"Args:   {json.dumps(tc.arguments)}\nResult: {tool_result}",
                )
                messages.append(
                    Message(
                        role="tool",
                        content=tool_result,
                        tool_call_id=tc.id,
                    )
                )
        else:
            logger.warning("Reached max_tool_rounds (%d) without a final answer.", max_tool_rounds)
            result.final_answer = "(max tool rounds reached)"

        calls_summary = ", ".join(r.name for r in result.tool_calls_made) or "none"
        self.print_result(f"Tools used: {calls_summary}\n\n{result.final_answer}")
        return result
