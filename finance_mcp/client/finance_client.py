import asyncio
import sys

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


def print_header(title: str):
    width = 60
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_report(result):
    text = " ".join(c.text for c in result.content if hasattr(c, "text"))
    # render **bold** markers as uppercase section headers
    lines = text.replace("\\n", "\n").split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("**") and stripped.endswith("**"):
            print(f"\n{stripped.replace('**', '').upper()}")
        else:
            clean = stripped.replace("**", "")
            if clean:
                print(f"  {clean}")


async def analyze_symbol(risk_session, symbol):
    print_header(f"FINANCIAL RISK ANALYSIS  |  {symbol}")
    print("  Fetching market data, research & running AI analysis...")

    result = await risk_session.call_tool(
        "intelligent_risk_analysis",
        {"symbol": symbol}
    )

    print_header(f"FINAL REPORT  |  {symbol}")
    print_report(result)
    print("\n" + "=" * 60 + "\n")


async def run_repl():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["../servers/risk_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as risk_session:
            await risk_session.initialize()

            print_header("FINANCE CLIENT")
            print("  Enter a ticker symbol (e.g. AAPL). Type 'End' or 'Quit' to exit.")

            while True:
                try:
                    symbol = await asyncio.to_thread(input, "\nSymbol> ")
                except EOFError:
                    break

                symbol = symbol.strip()
                if not symbol:
                    continue
                if symbol.lower() in ("end", "quit"):
                    break

                await analyze_symbol(risk_session, symbol.upper())


if __name__ == "__main__":
    asyncio.run(run_repl())
