# Scenario 5: enforce data authorization before the LLM

This scenario compares two authenticated MCP servers over the same SQLite data.
Both expose a tool named `list_my_expense_reports`, but they have very different
security boundaries.

| Version | Port | What enters the LLM context? |
| --- | ---: | --- |
| Vulnerable | 9100 | Every user's rows; the prompt merely asks the LLM to hide other users |
| Fixed | 9200 | Only rows owned by the identity derived from the verified token |

The lesson is not whether the model follows the instruction. Once another user's
record is returned by the tool, confidential data has already crossed the
authorization boundary and entered a third-party component's context, logs, and
possibly retention systems.

## Run it

Start Keycloak from scenario 3 first:

```bash
cd scenario3/keycloak
docker compose up -d
```

Install dependencies and start the demo:

```bash
cd scenario5
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python run_demo.py
```

Open `http://127.0.0.1:9300` for the recommended classroom experience. The UI
provides a working chat on the left and a context inspector on the right. The
inspector highlights every record returned by MCP, flags cross-user rows, and lets
students replay the same prompt against the fixed server.

The demo credentials are `alice` / `password` and `bob` / `password`. Credentials
are sent only to the local web process to obtain a Keycloak token; they are not
stored. Set `OLLAMA_HOST` and `OLLAMA_MODEL` if your Ollama configuration differs.
The header checks Keycloak, both MCP endpoints, and Ollama and marks unavailable
services in red.

The Scenario 5 defaults are:

```text
OLLAMA_HOST=http://localhost:11234
OLLAMA_MODEL=ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit
```

To run each component independently for debugging:

```bash
python server_vulnerable.py  # terminal 1, port 9100
python server_fixed.py       # terminal 2, port 9200
python web_app.py            # terminal 3, port 9300
```

## Classroom flow

Start in the vulnerable view as Alice and ask the assistant to summarize her
reports. The context inspector will show that Bob's rows entered the model even if
the answer only mentions Alice. Next, use the built-in prompt-injection suggestion,
then select **Replay this prompt against the fixed version**. In the fixed view,
Bob's rows never leave SQLite and therefore cannot appear in the model context.

## Why the fixed version works

`server_fixed.py` reads identity from the Authorization header after FastMCP's
`JWTVerifier` has accepted the token. The MCP tool has no `username` or `owner_id`
parameter for the model to manipulate. The repository maps the token's
`preferred_username` to the local user ID and includes that ID constraint in the
SQL query:

```sql
WHERE reports.owner_id = (
    SELECT id FROM users WHERE username = ?
)
```

Authentication alone is not enough: both versions validate the JWT. The security
difference is object-level authorization at the data access layer.

## Test the boundary without Keycloak or Ollama

```bash
python -m unittest -v test_access_control.py
```

The JWT used by the unit test is intentionally fake. It tests claim-to-query wiring,
not JWT verification; production requests are verified by FastMCP before tool code
runs.
