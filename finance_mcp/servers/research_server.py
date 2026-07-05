from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient
from dotenv import load_dotenv
import os

load_dotenv()

mcp = FastMCP("research-server")

tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


@mcp.tool()
def company_news(company: str) -> str:

    response = tavily.search(
        query=f"Latest financial news about {company}",
        max_results=5
    )

    return str(response)


@mcp.tool()
def analyst_sentiment(company: str) -> str:

    response = tavily.search(
        query=f"{company} stock analyst sentiment"
    )

    return str(response)


@mcp.tool()
def market_risks(company: str) -> str:

    response = tavily.search(
        query=f"{company} market risks lawsuits regulations"
    )

    return str(response)


if __name__ == "__main__":

    print("Starting Research MCP Server...")

    mcp.run()