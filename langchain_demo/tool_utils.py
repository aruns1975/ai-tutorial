"""
Shared helper for executing model-requested tool calls.

Keeps the "which tool does this name map to" lookup out of concept
files that need to execute tools by name (e.g. tool_calling.py) —
build the lookup once via create_tool_caller(), then call the
returned closure with whatever name/args the model produced.
"""

from collections.abc import Callable
from typing import Any


def create_tool_caller(tools: list[Callable]) -> Callable[[str, dict], Any]:
    """
    Given a list of plain Python functions, return a closure that
    looks a tool up by name and invokes it with args unpacked as
    keyword arguments.

    Usage:
        call_tool = create_tool_caller([adder, subtractor])
        call_tool("adder", {"a": 1, "b": 2})  # -> 3

    A tool that raises (e.g. a missing API key) doesn't propagate —
    the exception is caught and returned as a string instead, so the
    caller can feed it back to the model as the tool's result rather
    than crashing the whole request.
    """
    tools_by_name = {tool.__name__: tool for tool in tools}

    def call_tool(name: str, args: dict) -> Any:
        try:
            return tools_by_name[name](**args)
        except Exception as exc:
            return f"Error calling tool '{name}': {exc}"

    return call_tool
