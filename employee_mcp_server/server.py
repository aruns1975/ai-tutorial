"""
Builds the employee MCP server: a second, independent FastMCP instance
exposing employee CRUD tools (tools.py) over streamable-http.

This is a standalone server, distinct from mcp_server/ (this project's
original MCP server) — its own process, its own port
(EMPLOYEE_MCP_SERVER_PORT), its own in-memory store. It exists to
demonstrate that an MCP client can connect to more than one MCP server
side by side: langchain_mcp_adapters' MultiServerMCPClient (already used
by langchain_demo/mcp_client.py and langgraph_demo/mcp_client.py) is
built for exactly that, by taking a dict of named server configs rather
than a single URL. See docs/employee-mcp-server.md for the full design.

run_employee_mcp_server.py (project root) is the thin entry point that
actually runs this server, mirroring run_mcp_server.py's relationship to
mcp_server/server.py.
"""

import os

from mcp.server.fastmcp import FastMCP

from employee_mcp_server.tools import register_tools


def build_server() -> FastMCP:
    port = int(os.getenv("EMPLOYEE_MCP_SERVER_PORT", "18384"))
    mcp = FastMCP("ai-tutorial-employees", host="0.0.0.0", port=port)
    register_tools(mcp)
    return mcp


# Built once at import time, like mcp_server/server.py's mcp_app.
employee_mcp_app = build_server()