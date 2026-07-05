import asyncio
import os
import sys

from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from groq import Groq

load_dotenv()

mcp = FastMCP("risk-server")

# ==================================================
# GROQ CLIENT
# ==================================================

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def extract_text(result) -> str:
    return " ".join(c.text for c in result.content if hasattr(c, "text"))


# ==================================================
# RISK ANALYSIS TOOL
# ==================================================

@mcp.tool()
async def intelligent_risk_analysis(symbol: str) -> str:

    servers_dir = os.path.dirname(os.path.abspath(__file__))

    market_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(servers_dir, "market_server.py")]
    )

    research_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(servers_dir, "research_server.py")]
    )

    async with stdio_client(market_params) as (m_read, m_write):
        async with ClientSession(m_read, m_write) as market_session:
            await market_session.initialize()

            async with stdio_client(research_params) as (r_read, r_write):
                async with ClientSession(r_read, r_write) as research_session:
                    await research_session.initialize()

                    # ==========================================
                    # MARKET DATA
                    # ==========================================

                    stock_price = extract_text(await market_session.call_tool(
                        "get_stock_price", {"symbol": symbol}
                    ))

                    stock_history = extract_text(await market_session.call_tool(
                        "get_stock_history", {"symbol": symbol}
                    ))

                    stock_volatility = extract_text(await market_session.call_tool(
                        "get_stock_volatility", {"symbol": symbol}
                    ))

                    # ==========================================
                    # RESEARCH DATA
                    # ==========================================

                    company_news = extract_text(await research_session.call_tool(
                        "company_news", {"company": symbol}
                    ))

                    analyst_sentiment = extract_text(await research_session.call_tool(
                        "analyst_sentiment", {"company": symbol}
                    ))

                    market_risks = extract_text(await research_session.call_tool(
                        "market_risks", {"company": symbol}
                    ))

                    # ==========================================
                    # BUILD PROMPT
                    # ==========================================

                    risk_prompt = f"""

You are a Senior Financial Risk Officer.

Analyze investment risk for stock: {symbol}

==========================================
MARKET DATA
==========================================

STOCK PRICE:
{stock_price}

VOLATILITY:
{stock_volatility}

STOCK HISTORY:
{stock_history}

==========================================
RESEARCH DATA
==========================================

COMPANY NEWS:
{company_news}

ANALYST SENTIMENT:
{analyst_sentiment}

MARKET RISKS:
{market_risks}

==========================================

Provide:

1. Overall Risk Score (1-10)
2. Risk Category
3. Top 5 Risks
4. Investment Outlook
5. Suggested Allocation
6. Confidence Score
7. Executive Summary

Respond professionally.
"""

                    # ==========================================
                    # CALL GROQ LLM
                    # ==========================================

                    response = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {
                                "role": "system",
                                "content": "You are an expert financial risk analyst."
                            },
                            {
                                "role": "user",
                                "content": risk_prompt
                            }
                        ],
                        temperature=0.2,
                        max_tokens=1500
                    )

                    final_analysis = response.choices[0].message.content

                    return final_analysis


if __name__ == "__main__":

    print("Starting Risk MCP Server...")

    mcp.run()