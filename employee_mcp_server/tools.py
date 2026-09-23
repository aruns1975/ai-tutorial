"""
Tools exposed by the employee MCP server: CRUD operations on an
in-memory Employee store (employee_mcp_server/store.py).

Registered via mcp.add_tool(fn), the same registration style
mcp_server/tools.py uses for its tools/*.py subset — these five
functions are this server's own equivalent of that shared library, just
scoped to this standalone server's own domain (employee records) rather
than tools/, since CRUD state isn't a general-purpose, framework-agnostic
function meant to be imported directly by langchain_demo/langgraph_demo.
"""

from mcp.server.fastmcp import FastMCP

from employee_mcp_server.store import (
    create_employee,
    delete_employee,
    get_employee,
    list_employees,
    update_employee,
)

_MCP_TOOLS = [create_employee, get_employee, update_employee, delete_employee, list_employees]


def register_tools(mcp: FastMCP) -> None:
    for tool in _MCP_TOOLS:
        mcp.add_tool(tool)