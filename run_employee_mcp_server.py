"""
Entry point for the employee MCP server — the second of this project's
two MCP servers (see mcp_server/ and run_mcp_server.py for the first).
Run directly (`uv run python run_employee_mcp_server.py`, or via
scripts/start_employee_mcp_server.sh) to serve employee_mcp_server/'s
CRUD tools over streamable-http on EMPLOYEE_MCP_SERVER_PORT (default
18384) — a separate process/port from both the FastAPI app (main.py,
port 18282) and the original MCP server (run_mcp_server.py, port 18383).

Not named employee_mcp.py for the same reason run_mcp_server.py isn't
named mcp.py: no chance of shadowing the installed `mcp` PyPI package,
and it mirrors that file's "thin root entry point + package that does
the real work" shape.
"""

from employee_mcp_server.server import employee_mcp_app

if __name__ == "__main__":
    employee_mcp_app.run(transport="streamable-http")