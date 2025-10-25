import os, sys, argparse, asyncio, json, httpx
from typing import Any, Dict, List, Optional
from fastmcp import Client
import ollama

# ----------------------------
# Keycloak / MCP configuration
# ----------------------------
KC_URL   = os.getenv("KEYCLOAK_URL", "http://127.0.0.1:8080")
REALM    = os.getenv("KEYCLOAK_REALM", "mcp-lab")
AUD      = os.getenv("KEYCLOAK_AUDIENCE", "mcp-client")
TOKEN_EP = f"{KC_URL}/realms/{REALM}/protocol/openid-connect/token"
MCP_URL  = os.getenv("MCP_URL", "http://127.0.0.1:9000/mcp")

# ----------------------------
# Ollama configuration
# ----------------------------
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen3-vl:235b-cloud"


def get_token(username: str, password: str) -> str:
    data = {
        "grant_type": "password",
        "client_id": AUD,
        "scope": "openid",
        "username": username,
        "password": password,
    }
    r = httpx.post(TOKEN_EP, data=data, timeout=10.0)
    r.raise_for_status()
    return r.json()["id_token"]  # use ID token in this lab


# ----------------------------
# Utility: convert MCP tool -> Ollama tool schema
# ----------------------------
def mcp_tools_to_ollama(tools: List[Any]) -> List[Dict[str, Any]]:
    """
    FastMCP list_tools() returns objects with at least:
      - name: str
      - description: Optional[str]
      - inputSchema: dict (JSON Schema for the tool's input)
    Ollama expects OpenAI-style "tools" array:
      [{"type": "function", "function": {"name": ..., "description": ..., "parameters": {JSON Schema}}}]
    """
    out = []

    for t in tools:
        name = getattr(t, "name", None) #or t.get("name")
        desc = getattr(t, "description", None) #or t.get("description") or ""
        schema = getattr(t, "inputSchema", None) or t.get("inputSchema") or {"type": "object", "properties": {}}
        out.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": schema,
            },
        })
    return out


# ----------------------------
# Ollama chat call (sync), wrapped so we can await
# ----------------------------
def _ollama_chat_sync(model: str, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    client = ollama.Client(
        host=OLLAMA_HOST
    )
    return client.chat(model=model, messages=messages, tools=tools or [])

async def ollama_chat(model: str, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    # Run sync call in a thread to avoid blocking the event loop
    return await asyncio.to_thread(_ollama_chat_sync, model, messages, tools)

# ----------------------------
# Tool-using Agent
# ----------------------------
AGENT_SYSTEM_PROMPT = (
    "You are an AI agent connected to an MCP server. "
    "You can call tools when useful. "
    "Always prefer precise tool calls with minimal arguments. "
    "If a tool returns JSON, read it and continue reasoning. "
    "If no tool is needed, answer directly and clearly."
)

async def run_agent(client: Client, *, model: str, user_prompt: str) -> None:
    # Discover tools and expose them to the LLM
    tools = await client.list_tools()
    tool_names = [t.name for t in tools]
    print("Discovered MCP tools:", tool_names)

    ollama_tools = mcp_tools_to_ollama(tools)

    async def one_turn(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Ask the model. It may return tool calls.
        resp = await ollama_chat(model, messages, tools=ollama_tools)
        msg = resp.get("message") or resp.get("choices", [{}])[0].get("message", {})
        messages.append({"role": "assistant", "content": msg.get("content", "")})

        tool_calls = msg.get("tool_calls") or []
        for tc in tool_calls:
            # Structure: {"id": "...", "type": "function", "function": {"name": "...", "arguments": "<json>"}}
            fn = tc.get("function", {})
            name = fn.get("name")
            raw_args = fn.get("arguments", "{}")

            # Parse args safely
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except Exception:
                args = {}
            print(f"[agent] Calling tool: {name}({args})")

            # Execute the MCP tool
            try:
                result = await client.call_tool(name, args or {})
                payload = {"ok": True, "tool": name, "data": result.data}
            except Exception as e:
                payload = {"ok": False, "tool": name, "error": str(e)}

            # Send the tool result back to the model
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id"),  # helps models track which call this result belongs to
                "name": name,
                "content": json.dumps(payload),
            })

            # After each tool result, let the model continue reasoning
            resp = await ollama_chat(model, messages, tools=ollama_tools)
            msg = resp.get("message") or resp.get("choices", [{}])[0].get("message", {})
            messages.append({"role": "assistant", "content": msg.get("content", "")})

        return messages

  
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    messages = await one_turn(messages)
    print("\nagent>", messages[-1]["content"])


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()

    token = get_token(args.username, args.password)
    print("Got token...")

    # Pass token via auth=<token>; FastMCP sets Authorization: Bearer <token>
    async with Client(MCP_URL, auth=token) as client:
        # if args.prompt:
        await run_agent(client, model=OLLAMA_MODEL, user_prompt=args.prompt)
        # else:
            # print("\nNo agent prompt provided. Use --prompt '...' or --interactive to chat with the agent.")

if __name__ == "__main__":
    asyncio.run(main())
