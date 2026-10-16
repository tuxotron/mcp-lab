import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx
import ollama
from fastmcp import Client
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://127.0.0.1:8080")
REALM = os.getenv("KEYCLOAK_REALM", "mcp-lab")
AUDIENCE = os.getenv("KEYCLOAK_AUDIENCE", "mcp-client")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11234")
OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL", "ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit"
)
MCP_URLS = {
    "vulnerable": os.getenv("MCP_VULNERABLE_URL", "http://127.0.0.1:9100/mcp"),
    "fixed": os.getenv("MCP_FIXED_URL", "http://127.0.0.1:9200/mcp"),
}


async def get_token(username: str, password: str) -> str:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": AUDIENCE,
                "scope": "openid",
                "username": username,
                "password": password,
            },
        )
    response.raise_for_status()
    return response.json()["id_token"]


def clean_history(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    history: list[dict[str, str]] = []
    for item in value[-12:]:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            continue
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            history.append({"role": item["role"], "content": content[:4000]})
    return history


async def ask_ollama(
    *, username: str, message: str, history: list[dict[str, str]], records: list[dict]
) -> str:
    model_messages: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are an expense assistant. If not specified, the user is "
                f"{username}. Answer using the MCP data below."
                "MCP TOOL RESULT:\n"
                + json.dumps(records, indent=2)
            ),
        },
        *history,
        {"role": "user", "content": message},
    ]
    client = ollama.AsyncClient(host=OLLAMA_HOST)
    response = await client.chat(model=OLLAMA_MODEL, messages=model_messages)
    response_message = getattr(response, "message", None) or response["message"]
    content = getattr(response_message, "content", None)
    if content is None:
        content = response_message["content"]
    return content


async def chat(request: Request) -> JSONResponse:
    started = time.perf_counter()
    try:
        payload = await request.json()
    except (json.JSONDecodeError, ValueError):
        return JSONResponse({"error": "Request body must be valid JSON."}, status_code=400)

    version = payload.get("version")
    username = payload.get("username")
    password = payload.get("password")
    message = payload.get("message")

    if version not in MCP_URLS:
        return JSONResponse({"error": "Choose the vulnerable or fixed version."}, status_code=400)
    if not isinstance(username, str) or not username.strip():
        return JSONResponse({"error": "Username is required."}, status_code=400)
    if not isinstance(password, str) or not password:
        return JSONResponse({"error": "Password is required."}, status_code=400)
    if not isinstance(message, str) or not message.strip():
        return JSONResponse({"error": "Write a message first."}, status_code=400)

    username = username.strip()
    try:
        token = await get_token(username, password)
        async with Client(MCP_URLS[version], auth=token) as mcp_client:
            tool_result = await mcp_client.call_tool("list_my_expense_reports", {})
        records = tool_result.data
        if not isinstance(records, list):
            raise TypeError("MCP tool returned an unexpected payload")

        other_records = [record for record in records if record.get("owner") != username]
        answer = await ask_ollama(
            username=username,
            message=message.strip()[:4000],
            history=clean_history(payload.get("history")),
            records=records,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {400, 401}:
            error = "Keycloak rejected the demo credentials. Check the username and password."
            status = 401
        else:
            error = "Keycloak is unavailable or returned an error."
            status = 502
        return JSONResponse({"error": error}, status_code=status)
    except httpx.ConnectError:
        return JSONResponse(
            {"error": "A required local service is offline. Check Keycloak and the selected MCP server."},
            status_code=503,
        )
    except Exception as exc:
        return JSONResponse(
            {
                "error": "The local demo could not complete the request.",
                "detail": str(exc),
            },
            status_code=502,
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return JSONResponse(
        {
            "answer": answer,
            "trace": {
                "version": version,
                "authenticated_as": username,
                "tool": "list_my_expense_reports",
                "mcp_url": MCP_URLS[version],
                "records": records,
                "record_count": len(records),
                "other_user_count": len(other_records),
                "other_owners": sorted({record["owner"] for record in other_records}),
                "boundary_status": "breached" if other_records else "enforced",
                "elapsed_ms": elapsed_ms,
                "policy": (
                    "SELECT all rows; prompt asks the LLM to filter"
                    if version == "vulnerable"
                    else "WHERE owner_id = token-derived local user ID"
                ),
            },
        }
    )


async def health(_: Request) -> JSONResponse:
    async def is_reachable(url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(url)
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    keycloak, vulnerable, fixed, ollama_online = await asyncio.gather(
        is_reachable(f"{KEYCLOAK_URL}/realms/{REALM}"),
        is_reachable(MCP_URLS["vulnerable"]),
        is_reachable(MCP_URLS["fixed"]),
        is_reachable(f"{OLLAMA_HOST}/api/tags"),
    )
    return JSONResponse(
        {
            "status": "ok",
            "model": OLLAMA_MODEL,
            "services": {
                "keycloak": keycloak,
                "mcp": vulnerable and fixed,
                "ollama": ollama_online,
            },
        }
    )


async def index(_: Request) -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app = Starlette(
    debug=False,
    routes=[
        Route("/", index),
        Route("/api/chat", chat, methods=["POST"]),
        Route("/api/health", health),
        Mount("/static", app=StaticFiles(directory=STATIC_DIR), name="static"),
    ],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9300)
