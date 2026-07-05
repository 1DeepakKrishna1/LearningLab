from mcp.server.fastmcp import FastMCP
import yfinance as yf

mcp = FastMCP("market-server")


@mcp.tool()
def get_stock_price(symbol: str) -> str:

    ticker = yf.Ticker(symbol)

    history = ticker.history(period="1d")

    latest_price = round(
        history["Close"].iloc[-1],
        2
    )

    return f"{symbol} latest stock price is {latest_price}"


@mcp.tool()
def get_stock_history(symbol: str) -> str:

    ticker = yf.Ticker(symbol)

    history = ticker.history(period="30d")

    history = history[["Close", "Volume"]]

    return history.tail(10).to_string()


@mcp.tool()
def get_stock_volatility(symbol: str) -> str:

    ticker = yf.Ticker(symbol)

    history = ticker.history(period="30d")

    returns = history["Close"].pct_change()

    volatility = returns.std() * 100

    return f"{symbol} volatility is {round(volatility, 2)}%"


if __name__ == "__main__":

    print("Starting Market MCP Server...")

    mcp.run()