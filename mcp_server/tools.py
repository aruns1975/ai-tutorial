"""
Tools exposed by this project's MCP server — two ways to register one.

1. mcp.add_tool(fn) on a curated subset of tools/*.py functions, as-is —
   the exact same functions langchain_demo/tool_calling.py and
   langchain_demo/react_agent.py bind directly with bind_tools().
   Nothing about the functions changes; only HOW a caller reaches them
   does (the MCP protocol over HTTP here, vs. a local Python import
   there). This is the right choice whenever the tool is (or could be)
   also used outside MCP — tools/*.py must stay plain, undecorated
   functions so it keeps working as a framework-agnostic library, per
   the project root CLAUDE.md.

2. The @mcp.tool() decorator, used below for server_uptime_seconds — an
   MCP-only tool with no reason to live in tools/*.py, since its answer
   depends on this server process's own start time (_SERVER_START_TIME),
   not on inputs a shared, reusable function could take. Decorating it
   in place and mcp.add_tool(fn) build the exact same kind of Tool
   (name/description/schema all read from the function's name, docstring,
   and type hints — verified via mcp.server.fastmcp.FastMCP.tool()'s
   signature, which mirrors add_tool()'s); the decorator is just more
   direct when the function has no other caller to share it with.

Either way, tools/*.py's docstring convention (module docstring + "Call
this tool for..." + few-shot examples) is what a tool-calling model
reads to pick the right tool, so server_uptime_seconds follows it too
even though it isn't in tools/*.py.
"""

import time

from mcp.server.fastmcp import FastMCP

from tools.conversion_tools import celsius_to_fahrenheit, km_to_miles
from tools.datetime_tools import current_date, days_between
from tools.geometry_tools import circle_area, rectangle_area
from tools.math_tools import adder, divider, multiplier, subtractor
from tools.search_tools import web_search
from tools.string_tools import is_palindrome, reverse_text, word_count

_MCP_TOOLS = [
    adder,
    subtractor,
    multiplier,
    divider,
    reverse_text,
    word_count,
    is_palindrome,
    current_date,
    days_between,
    circle_area,
    rectangle_area,
    celsius_to_fahrenheit,
    km_to_miles,
    web_search,
]

# Set once at import time (this module is only ever imported once, when
# mcp_server/server.py builds the singleton mcp_app), so it marks this
# server process's actual start time.
_SERVER_START_TIME = time.monotonic()


def register_tools(mcp: FastMCP) -> None:
    for tool in _MCP_TOOLS:
        mcp.add_tool(tool)

    @mcp.tool()
    def server_uptime_seconds() -> float:
        """
        Return how many seconds this MCP server process has been running.

        Call this tool for requests like "how long has the MCP server
        been up" or "what's the server's uptime". Route away to
        current_date if the user wants today's date rather than elapsed
        server uptime.

        Few-shot examples (phrase -> tool call):
            "How long has the MCP server been running?"
                                        -> server_uptime_seconds()
            "What's the server uptime?" -> server_uptime_seconds()
        """
        return time.monotonic() - _SERVER_START_TIME
