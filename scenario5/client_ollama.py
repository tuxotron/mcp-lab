import argparse
import asyncio
import json
import os
from typing import Any

import httpx
import ollama
from fastmcp import Client


KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://127.0.0.1:8080")
REALM = os.getenv("KEYCLOAK_REALM", "mcp-lab")
AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "mcp-client")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11234")
OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL", "ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit"
)


def get_token(username: str, password: str) -> str:
    response = httpx.post(
        f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": AUDIENCE,
            "scope": "openid",
            "username": username,
            "password": password,
        },
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()["id_token"]


def to_ollama_tools(tools: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in tools
    ]


async def run_agent(client: Client, prompt: str) -> None:
    mcp_tools = await client.list_tools()
    tools = to_ollama_tools(mcp_tools)
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are an expense assistant. Use MCP tools to answer questions. "
                "Only reveal records belonging to the authenticated user."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    ollama_client = ollama.AsyncClient(host=OLLAMA_HOST)
    response = await ollama_client.chat(model=OLLAMA_MODEL, messages=messages, tools=tools)
    assistant_message = getattr(response, "message", None) or response["message"]
    messages.append(assistant_message)

    tool_calls = getattr(assistant_message, "tool_calls", None)
    if tool_calls is None:
        tool_calls = assistant_message.get("tool_calls") or []

    for call in tool_calls:
        function = getattr(call, "function", None) or call["function"]
        function_name = getattr(function, "name", None) or function["name"]
        arguments = getattr(function, "arguments", None)
        if arguments is None and isinstance(function, dict):
            arguments = function.get("arguments")
        arguments = arguments or {}
        if isinstance(arguments, str):
            arguments = json.loads(arguments)

        result = await client.call_tool(function_name, arguments)
        print("\nData returned by MCP and inserted into the LLM context:")
        print(json.dumps(result.data, indent=2))
        messages.append(
            {
                "role": "tool",
                "tool_name": function_name,
                "content": json.dumps(result.data),
            }
        )

    if tool_calls:
        response = await ollama_client.chat(model=OLLAMA_MODEL, messages=messages, tools=tools)

    final_message = getattr(response, "message", None) or response["message"]
    final_content = getattr(final_message, "content", None)
    if final_content is None:
        final_content = final_message["content"]
    print("\nAssistant response:")
    print(final_content)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", default="alice")
    parser.add_argument("--password", default="password")
    parser.add_argument(
        "--version", choices=("vulnerable", "fixed"), default="vulnerable"
    )
    parser.add_argument("--prompt", default="Show me my expense reports")
    args = parser.parse_args()

    default_urls = {
        "vulnerable": "http://127.0.0.1:9100/mcp",
        "fixed": "http://127.0.0.1:9200/mcp",
    }
    mcp_url = os.getenv("MCP_URL", default_urls[args.version])
    token = get_token(args.username, args.password)

    async with Client(mcp_url, auth=token) as client:
        await run_agent(client, args.prompt)


if __name__ == "__main__":
    asyncio.run(main())
