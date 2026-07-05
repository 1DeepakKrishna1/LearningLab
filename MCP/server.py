#!/usr/bin/env python3
"""MCP Server exposing Calculator and Stock Price tools."""

import asyncio

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

# ---------------------------------------------------------------------------
# Dummy stock data
# ---------------------------------------------------------------------------
STOCK_DATA: dict[str, float] = {
    "AAPL": 182.52,
    "GOOGL": 141.80,
    "MSFT": 415.26,
    "AMZN": 178.75,
    "TSLA": 248.42,
    "META": 501.30,
    "NVDA": 875.40,
    "NFLX": 628.15,
    "AMD": 178.92,
    "INTC": 43.56,
    "UBER": 72.34,
    "LYFT": 16.88,
    "PYPL": 65.21,
    "SNAP": 11.47,
    "SPOT": 245.60,
}

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------
server = Server("mcp-demo-server")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="calculator",
            description=(
                "Perform basic arithmetic operations: add, subtract, multiply, divide. "
                "Supports integer and floating-point numbers."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "The arithmetic operation to perform.",
                    },
                    "a": {
                        "type": "number",
                        "description": "The first operand.",
                    },
                    "b": {
                        "type": "number",
                        "description": "The second operand.",
                    },
                },
                "required": ["operation", "a", "b"],
            },
        ),
        types.Tool(
            name="get_stock_price",
            description=(
                "Return the current (dummy) stock price for a given ticker symbol. "
                f"Supported tickers: {', '.join(sorted(STOCK_DATA))}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol, e.g. AAPL, GOOGL.",
                    }
                },
                "required": ["ticker"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------
@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    args = arguments or {}

    if name == "calculator":
        try:
            operation: str = args["operation"]
            a: float = float(args["a"])
            b: float = float(args["b"])
        except (KeyError, ValueError, TypeError) as exc:
            return [types.TextContent(type="text", text=f"Invalid arguments: {exc}")]

        match operation:
            case "add":
                result, symbol = a + b, "+"
            case "subtract":
                result, symbol = a - b, "−"
            case "multiply":
                result, symbol = a * b, "×"
            case "divide":
                if b == 0:
                    return [
                        types.TextContent(type="text", text="Error: division by zero.")
                    ]
                result, symbol = a / b, "÷"
            case _:
                return [
                    types.TextContent(
                        type="text", text=f"Unknown operation: '{operation}'"
                    )
                ]

        # Format integers cleanly
        fmt = lambda v: int(v) if v == int(v) else round(v, 10)
        text = f"{fmt(a)} {symbol} {fmt(b)} = {fmt(result)}"
        return [types.TextContent(type="text", text=text)]

    if name == "get_stock_price":
        ticker: str = str(args.get("ticker", "")).strip().upper()
        if not ticker:
            return [types.TextContent(type="text", text="Error: ticker is required.")]

        price = STOCK_DATA.get(ticker)
        if price is None:
            available = ", ".join(sorted(STOCK_DATA))
            return [
                types.TextContent(
                    type="text",
                    text=(
                        f"Ticker '{ticker}' not found in dummy data. "
                        f"Available tickers: {available}."
                    ),
                )
            ]
        return [
            types.TextContent(
                type="text", text=f"{ticker} current price: ${price:.2f}"
            )
        ]

    return [types.TextContent(type="text", text=f"Unknown tool: '{name}'")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-demo-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
