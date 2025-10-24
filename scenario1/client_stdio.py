import asyncio
from fastmcp import Client

async def main():
    # When you pass a filename, FastMCP Client uses stdio to spawn the process
    async with Client("server_stdio.py") as client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools])

        r1 = await client.call_tool("echo", {"text": "hello MCP"})
        print("echo ->", r1.data)

        r2 = await client.call_tool("add", {"a": 2, "b": 40})
        print("add ->", r2.data)

        r3 = await client.call_tool("now_iso", {})
        print("now_iso ->", r3.data)

if __name__ == "__main__":
    asyncio.run(main())
