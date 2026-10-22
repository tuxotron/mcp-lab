from fastmcp import Context, FastMCP

from auth import username_from_verified_token
from database import get_reports_for_username
from server_common import jwt_verifier


mcp = FastMCP("Expense Reports - Fixed", auth=jwt_verifier())


@mcp.tool
def list_my_expense_reports(context: Context) -> list[dict]:
    """Return only expense reports owned by the authenticated caller."""
    authorization = context.request_context.request.headers.get("Authorization")
    username = username_from_verified_token(authorization)

    # The model cannot supply or override username. It comes from the verified token,
    # and the ownership constraint is applied before any data leaves SQLite.
    return get_reports_for_username(username)


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=9200, path="/mcp")
