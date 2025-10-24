from fastmcp import FastMCP

mcp = FastMCP("Lab HTTP Server (No Auth)")

@mcp.tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b

@mcp.tool
def greet(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    # Start Streamable HTTP transport on /mcp (127.0.0.1:8000 by default)
    mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp")
