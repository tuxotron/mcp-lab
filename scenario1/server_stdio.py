from fastmcp import FastMCP, Context
import datetime

mcp = FastMCP("Lab STDIO Server")

@mcp.tool
def echo(text: str) -> str:
    """Echo back any text."""
    return text

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

@mcp.tool
def now_iso() -> str:
    """Return the current timestamp in ISO 8601."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

if __name__ == "__main__":
    # STDIO is default transport
    mcp.run()
