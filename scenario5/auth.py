import base64
import json
from typing import Any


def claims_from_verified_authorization_header(header: str | None) -> dict[str, Any]:
    """Read claims after FastMCP's JWTVerifier has authenticated the request.

    Decoding is not signature verification. This helper is safe here only because the
    MCP auth middleware rejects invalid tokens before invoking a tool.
    """
    if not header:
        raise PermissionError("Missing Authorization header")

    token = header.removeprefix("Bearer ").strip()
    parts = token.split(".")
    if len(parts) != 3 or not all(parts):
        raise PermissionError("Malformed bearer token")

    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, json.JSONDecodeError) as exc:
        raise PermissionError("Malformed token claims") from exc

    return claims


def username_from_verified_token(header: str | None) -> str:
    claims = claims_from_verified_authorization_header(header)
    username = claims.get("preferred_username")
    if not isinstance(username, str) or not username:
        raise PermissionError("Token has no preferred_username claim")
    return username
