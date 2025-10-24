import os, sys, argparse, asyncio, httpx
from fastmcp import Client

KC_URL   = os.getenv("KEYCLOAK_URL", "http://127.0.0.1:8080")
REALM    = os.getenv("KEYCLOAK_REALM", "mcp-lab")
AUD      = os.getenv("KEYCLOAK_AUDIENCE", "mcp-client")
TOKEN_EP = f"{KC_URL}/realms/{REALM}/protocol/openid-connect/token"
MCP_URL  = os.getenv("MCP_URL", "http://127.0.0.1:9000/mcp")

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
    # print("access_token: ", r.json()["access_token"])
    # print("id_token: ", r.json()["id_token"])
    return r.json()["id_token"]

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    token = get_token(args.username, args.password)
    print("Got token...")

    # Pass token via auth=<token>; FastMCP will set Authorization: Bearer <token>
    async with Client(MCP_URL, auth=token) as client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools])
        
        r = await client.call_tool("whoami", {})
        print("whoami ->", r.data)

        r = await client.call_tool("admin_only_demo", {})
        print("admin_only_demo ->", r.data)

        r = await client.call_tool("hello", {})
        print("hello ->", r.data)

if __name__ == "__main__":
    asyncio.run(main())
