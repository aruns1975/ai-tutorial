"""
Entry point for this project's MCP server — the MCP equivalent of
main.py. Run directly (`uv run python run_mcp_server.py`, or via
scripts/start_mcp_server.sh) to serve mcp_server/'s tools, prompts, and
resources over streamable-http on MCP_SERVER_PORT (default 18383).

Deliberately NOT named mcp.py: a root-level mcp.py would shadow the
installed `mcp` PyPI package itself (verified — once a repo-root mcp.py
exists, `from mcp.server.fastmcp import FastMCP` anywhere in this
project breaks with `ModuleNotFoundError: No module named 'mcp.server';
'mcp' is not a package`, since Python resolves the local same-named
file before site-packages).

A separate process/port from the FastAPI app (main.py, port 18282) —
langchain_demo/mcp_client.py and langgraph_demo/mcp_client.py connect
to this server as an HTTP client, the same way any external MCP client
would.
"""

from mcp_server.server import mcp_app

if __name__ == "__main__":
    mcp_app.run(transport="streamable-http")
