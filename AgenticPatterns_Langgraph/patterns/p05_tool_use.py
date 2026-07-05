"""
Pattern 05: Tool Use
====================
Concept: The LLM is given a set of tool schemas. When it decides to call a tool,
the graph routes to an execution node that runs the function and returns the
result. This loop continues until the LLM produces a final text response.

This pattern uses LangGraph's prebuilt `create_react_agent` which implements the
standard ReAct (Reasoning + Acting) loop out of the box.

Tools (all self-contained, no external APIs):
  - calculator        : evaluate safe math expressions
  - unit_converter    : convert between common units
  - get_current_date  : return today's date
  - currency_lookup   : mock exchange rates

Demo:   "Plan a 5-night stay in Tokyo: convert USD to JPY, calculate hotel cost,
         and find out what day the trip would start if departing tomorrow."
"""
from __future__ import annotations

import math
import traceback
from datetime import date, timedelta
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from core.base import BasePattern, PatternResult
from core.llm import MODEL_LARGE


# -------------------------------------------------------------------- tools

@tool
def calculator(expression: str) -> str:
    """Evaluate a safe mathematical expression.

    Args:
        expression: A mathematical expression string, e.g. '2 ** 10 + 5 * 3'.

    Returns:
        The numeric result as a string, or an error message.
    """
    allowed = set("0123456789+-*/().,% abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
    if not all(c in allowed for c in expression):
        return "Error: expression contains disallowed characters"
    try:
        safe_globals = {"__builtins__": {}, "math": math, "abs": abs, "round": round, "pow": pow}
        result = eval(expression, safe_globals, {})  # noqa: S307 — intentionally restricted
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@tool
def unit_converter(value: float, from_unit: str, to_unit: str) -> str:
    """Convert a numeric value between common units.

    Supports: km↔miles, kg↔lbs, celsius↔fahrenheit, usd↔jpy (approximate).

    Args:
        value: The numeric value to convert.
        from_unit: Source unit (e.g. 'km', 'kg', 'celsius', 'usd').
        to_unit: Target unit (e.g. 'miles', 'lbs', 'fahrenheit', 'jpy').

    Returns:
        Converted value with units as a string.
    """
    conversions: dict[tuple[str, str], float] = {
        ("km", "miles"): 0.621371,
        ("miles", "km"): 1.60934,
        ("kg", "lbs"): 2.20462,
        ("lbs", "kg"): 0.453592,
        ("usd", "jpy"): 149.5,
        ("jpy", "usd"): 1 / 149.5,
        ("usd", "eur"): 0.92,
        ("eur", "usd"): 1 / 0.92,
        ("celsius", "fahrenheit"): None,   # handled separately
        ("fahrenheit", "celsius"): None,
    }
    key = (from_unit.lower(), to_unit.lower())
    if key == ("celsius", "fahrenheit"):
        result = value * 9 / 5 + 32
    elif key == ("fahrenheit", "celsius"):
        result = (value - 32) * 5 / 9
    elif key in conversions:
        result = value * conversions[key]
    else:
        return f"Conversion from {from_unit} to {to_unit} is not supported."
    return f"{value} {from_unit} = {result:.2f} {to_unit}"


@tool
def get_current_date(offset_days: int = 0) -> str:
    """Return a calendar date relative to today.

    Args:
        offset_days: Number of days from today (0 = today, 1 = tomorrow, -1 = yesterday).

    Returns:
        ISO-formatted date string (YYYY-MM-DD) and the day of the week.
    """
    target = date.today() + timedelta(days=offset_days)
    return f"{target.isoformat()} ({target.strftime('%A')})"


@tool
def hotel_price_lookup(city: str, tier: str = "mid") -> str:
    """Look up approximate average nightly hotel prices in a city.

    Args:
        city: City name (e.g. 'Tokyo', 'Paris', 'New York').
        tier: Hotel tier — 'budget', 'mid', or 'luxury'.

    Returns:
        Average nightly price in USD.
    """
    prices: dict[str, dict[str, int]] = {
        "tokyo":    {"budget": 60,  "mid": 150, "luxury": 450},
        "paris":    {"budget": 80,  "mid": 200, "luxury": 600},
        "new york": {"budget": 100, "mid": 250, "luxury": 700},
        "london":   {"budget": 90,  "mid": 220, "luxury": 650},
        "bali":     {"budget": 30,  "mid": 80,  "luxury": 250},
    }
    city_key = city.lower().strip()
    city_prices = prices.get(city_key, {"budget": 70, "mid": 160, "luxury": 480})
    tier_key = tier.lower().strip()
    price = city_prices.get(tier_key, city_prices["mid"])
    return f"Average nightly rate in {city.title()} ({tier} tier): ${price} USD"


TOOLS = [calculator, unit_converter, get_current_date, hotel_price_lookup]


class PatternToolUse(BasePattern):
    PATTERN_NUMBER = 5
    PATTERN_NAME = "Tool Use"
    DESCRIPTION = (
        "ReAct loop: LLM reasons, calls tools, incorporates results, repeats until done."
    )

    # --------------------------------------------------------------- graph

    def build_graph(self) -> Any:
        llm_with_tools = self.llm.large.bind_tools(TOOLS)
        # create_react_agent builds the full ReAct graph internally
        return create_react_agent(llm_with_tools, TOOLS)

    # --------------------------------------------------------------- run

    def run(self, input_data: str, **kwargs) -> PatternResult:
        try:
            app = self.build_graph()
            messages = [HumanMessage(content=input_data)]
            final, elapsed_ms = self._timed_run(
                app.invoke, {"messages": messages}
            )

            # Extract all messages for step logging
            steps = []
            for msg in final["messages"]:
                msg_type = type(msg).__name__
                content = getattr(msg, "content", "") or ""
                tool_calls = getattr(msg, "tool_calls", [])
                steps.append({
                    "type": msg_type,
                    "content": str(content)[:200],
                    "tool_calls": [tc.get("name", "") for tc in (tool_calls or [])],
                })

            # Final answer is the last AIMessage
            final_answer = ""
            for msg in reversed(final["messages"]):
                if type(msg).__name__ == "AIMessage" and msg.content:
                    final_answer = msg.content
                    break

            tool_names_used = list({
                tc.get("name", "")
                for msg in final["messages"]
                for tc in getattr(msg, "tool_calls", []) or []
            })

            return self._make_result(
                success=True,
                input_data=input_data,
                output_data=final_answer,
                elapsed_ms=elapsed_ms,
                steps=steps,
                metadata={
                    "tools_used": tool_names_used,
                    "total_messages": len(final["messages"]),
                    "available_tools": [t.name for t in TOOLS],
                },
            )
        except Exception:
            return self._make_result(
                success=False,
                input_data=input_data,
                output_data=None,
                error=traceback.format_exc(),
            )
