from fastmcp import FastMCP, Context
from fastmcp.server.auth.providers.jwt import JWTVerifier
import base64, json

verifier = JWTVerifier(
    issuer="http://127.0.0.1:8080/realms/mcp-lab",
    jwks_uri="http://localhost:8080/realms/mcp-lab/protocol/openid-connect/certs",
    audience="mcp-client"
)

mcp = FastMCP("MyServer", auth=verifier)

def jwt_second_block(token: str) -> str:
    parts = token.split(".")
    if len(parts) != 3 or not all(parts):
        raise ValueError("Invalid JWT: expected 3 dot-separated parts")
    return parts[1]

def b64url_decode(b64url: str) -> bytes:
    padding = "=" * (-len(b64url) % 4)
    return base64.urlsafe_b64decode(b64url + padding)

def get_roles(token):
    claims = jwt_second_block(token)
    decoded = b64url_decode(claims)

    payload = json.loads(decoded)
    roles = set()

    roles.update(map(str, (payload.get("realm_access") or {}).get("roles", []) or []))
    return roles

def get_username(token):
    claims = jwt_second_block(token)
    decoded = b64url_decode(claims)

    payload = json.loads(decoded)
    return payload.get("preferred_username")

def is_admin(token):
    roles = get_roles(token)
    return "mcp-admin" in roles

def is_user(token):
    roles = get_roles(token)
    return "mcp-user" in roles


@mcp.tool
def whoami(context: Context) -> dict:
    """Return a simple description of this secure server."""

    user_token = context.request_context.request.headers.get("Authorization")
    if is_user(user_token):
        return {"service": "mcp-secure", "auth": "keycloak"}
    else:
        return {"service": "mcp-secure", "auth": "Not Authorized"}

@mcp.tool
def admin_only_demo(context: Context) -> str:
    user_token = context.request_context.request.headers.get("Authorization")
    if is_admin(user_token):    
        return "If you can call me, you have 'mcp-admin' role."
    else:
        return "Unauthorized"

@mcp.tool
def hello(context: Context) -> str:
    user_token = context.request_context.request.headers.get("Authorization")
    return f"Hello, {get_username(user_token)}!"

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=9000) 
