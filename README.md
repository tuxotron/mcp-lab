# Model Context Protocol Lab (Python + FastMCP)

This lab gives you **three** progressively more advanced MCP server scenarios using the **FastMCP** library:

1) **Local server over STDIO** (no network, great for local tools)
2) **HTTP (Streamable HTTP) server** without auth
3) **HTTP (Streamable HTTP) server** protected by **Keycloak** (OIDC), with JWT-based **authentication + role-based authorization**

---

## 🚀 Quick Start

For each scenario, run the following:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
---

## 1) Local MCP server over **STDIO**

Run server (stdio is default):
```bash
cd scenario1
source .venv/bin/activate
python server_stdio.py
```

In a **separate** terminal, run the simple test client:
```bash
cd scenario1
source .venv/bin/activate
python client_stdio.py
```

---

## 2) HTTP (Streamable HTTP) server (no auth)

Start server:
```bash
cd scenario2
source .venv/bin/activate
python server_http.py
# default: http://127.0.0.1:8000/mcp
```

Test with client:
```bash
cd scenario2
source .venv/bin/activate
python scenario2/client_http.py
```

---

## 3) HTTP (Streamable HTTP) server **with Keycloak authn/z**

### Start Keycloak
```bash
cd scenario3/keycloak
docker compose up -d
# Admin console: http://localhost:8080  (admin/admin)
# Realm: mcp-lab, Client: mcp-client (public), Roles: mcp-user, mcp-admin
# Users: alice (mcp-user), bob (mcp-admin) – password for both: password
```

Go to mcp-lab realm. Menu: Client Scopes. Select `roles` from the list, click on the `Mappers` tab, select `realm roles`, turn on `Add to ID token`. Save!

### Run secure MCP server
```bash
# back to root
cd scenario3
source .venv/bin/activate
python server_http_keycloak.py
# default: http://127.0.0.1:9000/mcp
```

### Call with a token (client)
```bash
cd scenario3
source .venv/bin/activate
python client_http_keycloak.py --username alice --password password   # has role mcp-user
python client_http_keycloak.py --username bob   --password password   # has role mcp-admin
```

## 4) Ollama tools calling

Start Keycloak and MCP server from scenario 3

```bash
cd scenario4
source .venv/bin/activate
```

Adjust the OLLAMA_HOST and OLLAMA_MODEL constants in `client-ollama.py`:

```python
# ----------------------------
# Ollama configuration
# ----------------------------
OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen3-vl:235b-cloud"
```

Then you could make a call like:

```bash
python client-ollama.py --username bob --password password --prompt "Who am I according to the server? Then say hello"
```

You should see something similar to:

```
Got token...
Discovered MCP tools: ['whoami', 'admin_only_demo', 'hello']
[agent] Calling tool: whoami({})
[agent] Calling tool: hello({})

agent> <think>
...
...
</think>

The server identifies itself as part of the "mcp-secure" service using Keycloak authentication. 

Hello, bob!
```

We can try with Alice as well:

```bash
python client-ollama.py --username alice --password password --prompt "Who am I according to the server? Then say hello"
```

You should see something like:

```
Discovered MCP tools: ['whoami', 'admin_only_demo', 'hello']
[agent] Calling tool: whoami({})
[agent] Calling tool: hello({})

agent> <think>
...
...
</think>

The server identifies itself as `mcp-secure` with authentication via `keycloak`. 

Hello, alice! How can I assist you today?
```

