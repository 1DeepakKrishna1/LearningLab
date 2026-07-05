# MCP Calculator & Stock Price Demo

A Python implementation of an **MCP (Model Context Protocol) Server** and **Client** that exposes two tools — a calculator and a stock-price lookup — powered by a **Groq LLM** agentic loop.

---

## Project Structure

```
MCP/
├── server.py          # MCP Server — exposes calculator & stock-price tools
├── client.py          # MCP Client — Groq-powered agentic REPL
├── requirements.txt   # Python dependencies
└── README.md
```

---

## Prerequisites

- Python 3.11+
- A [Groq API key](https://console.groq.com/keys)

---

## Installation

```bash
pip install -r requirements.txt
```

Set your Groq API key:

```bash
# Linux / macOS
export GROQ_API_KEY=gsk_...

# Windows (PowerShell)
$env:GROQ_API_KEY="gsk_..."

# Windows (CMD)
set GROQ_API_KEY=gsk_...
```

---

## Running

Start the client — it automatically launches the server as a subprocess:

```bash
python client.py
```

---

## MCP Server (`server.py`)

Runs over **stdio transport** and exposes two tools.

### Tool: `calculator`

Performs basic arithmetic on two numbers.

| Parameter   | Type   | Allowed values                          |
|-------------|--------|-----------------------------------------|
| `operation` | string | `add`, `subtract`, `multiply`, `divide` |
| `a`         | number | First operand                           |
| `b`         | number | Second operand                          |

Example call:
```json
{ "operation": "multiply", "a": 15, "b": 37 }
```
Returns: `15 × 37 = 555`

---

### Tool: `get_stock_price`

Returns a dummy stock price for a given ticker symbol.

| Parameter | Type   | Description                 |
|-----------|--------|-----------------------------|
| `ticker`  | string | Stock symbol, e.g. `AAPL`  |

Supported tickers: `AAPL`, `AMD`, `AMZN`, `GOOGL`, `INTC`, `LYFT`, `META`, `MSFT`, `NFLX`, `NVDA`, `PYPL`, `SNAP`, `SPOT`, `TSLA`, `UBER`

Example call:
```json
{ "ticker": "NVDA" }
```
Returns: `NVDA current price: $875.40`

---

## MCP Client (`client.py`)

The client:

1. Spawns `server.py` as a subprocess via stdio transport.
2. Calls `list_tools()` to discover available tools dynamically.
3. Converts MCP tool schemas to the Groq/OpenAI function-calling format.
4. Enters an **agentic loop**: sends the user's message to Groq (`llama-3.3-70b-versatile`), executes any tool calls via the MCP session, feeds results back, and repeats until the model signals `finish_reason: stop`.

### Agentic Loop Flow

```
User input
    │
    ▼
Groq LLM ──► finish_reason: stop ──► Print final answer
    │
    │ finish_reason: tool_calls
    ▼
Execute tool(s) via MCP Server
    │
    ▼
Feed tool results back to Groq
    │
    └──► (repeat)
```

### Example Session

```
[MCP] Connected. Tools available: ['calculator', 'get_stock_price']

MCP Client ready. (Powered by Groq · llama-3.3-70b-versatile)
Type a question, a calculation, or a multi-step plan.
Type 'quit' or press Ctrl-C to exit.

You: What is 15 multiplied by 37? Then add the NVDA stock price to that result.
Thinking...

  → calculator({"operation": "multiply", "a": 15, "b": 37})
  ← 15 × 37 = 555
  → get_stock_price({"ticker": "NVDA"})
  ← NVDA current price: $875.40

Assistant: 15 multiplied by 37 is 555, and adding NVDA's price of $875.40 gives **1430.40**.
```

---

## How the Tools Are Wired Together

The client never hardcodes tool logic. Tools are discovered dynamically at startup
via `list_tools()` and invoked via `call_tool()` over the MCP stdio transport.

```
client.py                              server.py
    |                                      |
    |-- stdio_client ---------------------->
    |   list_tools()                        |  [calculator, get_stock_price]
    |<--------------------------------------|
    |                                      |
    |   call_tool('calculator', {...})      |
    |--------------------------------------->|
    |<-- '15 x 37 = 555' ------------------|
```

---

## Configuration Reference

| Variable        | File       | Default                      | Description                      |
|-----------------|------------|------------------------------|----------------------------------|
| `MODEL`         | client.py  | `llama-3.3-70b-versatile`   | Groq model for the agentic loop  |
| `SERVER_SCRIPT` | client.py  | `server.py` (same directory) | Path to MCP server               |
| `SYSTEM_PROMPT` | client.py  | See source                   | LLM system instruction           |
| `STOCK_DATA`    | server.py  | 15 tickers                   | Dummy price table                |
