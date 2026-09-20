"""
Builds this project's MCP server: a single FastMCP instance exposing
tools (tools.py), prompts (prompts.py), and resources (resources.py)
over streamable-http — see docs/mcp-server.md for the full design.

run_mcp_server.py (project root) is the thin entry point that actually
runs this server, the same relationship main.py has to controllers/.
"""

import os

from mcp.server.fastmcp import FastMCP

from mcp_server.prompts import register_prompts
from mcp_server.resources import register_resources
from mcp_server.tools import register_tools


def build_server() -> FastMCP:
    port = int(os.getenv("MCP_SERVER_PORT", "18383"))
    mcp = FastMCP("ai-tutorial", host="0.0.0.0", port=port)
    register_tools(mcp)
    register_prompts(mcp)
    register_resources(mcp)
    return mcp


# Built once at import time, like controllers/__init__.py's `router` —
# run_mcp_server.py imports this singleton rather than rebuilding it.
mcp_app = build_server()
