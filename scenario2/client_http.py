import asyncio
from fastmcp import Client

URL = "http://127.0.0.1:8000/mcp"

async def main():
    async with Client(URL) as client:
        tools = await client.list_tools()
        # print("Tools:", [t.name for t in tools])
        print("Tools:", tools)

        r1 = await client.call_tool("multiply", {"a": 6, "b": 7})
        print("multiply ->", r1.data)

        r2 = await client.call_tool("greet", {"name": "Melissa"})
        print("greet ->", r2.data)

if __name__ == "__main__":
    asyncio.run(main())
