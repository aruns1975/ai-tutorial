"""
Tools exposed by this project's MCP server.

Registers a curated subset of tools/*.py functions as-is, via
mcp.add_tool() — the exact same functions langchain_demo/tool_calling.py
and langchain_demo/react_agent.py bind directly with bind_tools().
Nothing about the functions changes; only HOW a caller reaches them
does (the MCP protocol over HTTP here, vs. a local Python import
there). tools/*.py's docstring convention (module docstring + "Call
this tool for..." + few-shot examples) is exactly what a tool-calling
model reads to pick the right tool — that's true whether the tool is
bound locally or fetched over MCP, so no new docstrings are needed
here.
"""

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


def register_tools(mcp: FastMCP) -> None:
    for tool in _MCP_TOOLS:
        mcp.add_tool(tool)
