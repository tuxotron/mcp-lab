from fastmcp import Context, FastMCP

from database import get_all_reports
from server_common import jwt_verifier


mcp = FastMCP("Expense Reports - Vulnerable", auth=jwt_verifier())


@mcp.tool
def list_my_expense_reports(context: Context) -> list[dict]:
    """Return the authenticated user's expense reports.

    SECURITY BUG: despite the description, this tool returns the entire table and
    relies on the LLM to decide which rows the caller should see.
    """
    del context
    return get_all_reports()


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=9100, path="/mcp")
