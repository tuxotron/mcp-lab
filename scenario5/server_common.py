import os

from fastmcp.server.auth.providers.jwt import JWTVerifier


def jwt_verifier() -> JWTVerifier:
    keycloak_url = os.getenv("KEYCLOAK_URL", "http://127.0.0.1:8080")
    realm = os.getenv("KEYCLOAK_REALM", "mcp-lab")
    return JWTVerifier(
        issuer=f"{keycloak_url}/realms/{realm}",
        jwks_uri=f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs",
        audience=os.getenv("KEYCLOAK_AUDIENCE", "mcp-client"),
    )
