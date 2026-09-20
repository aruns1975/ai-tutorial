"""
Prompts exposed by this project's MCP server.

One prompt, deliberately themed around this repo's own subject matter
(LangChain/LangGraph concepts) rather than a generic example — an MCP
client fetching this prompt gets back the same kind of instruction-plus-
context template langchain_demo/prompts_and_parsers.py builds by hand
with ChatPromptTemplate, just sourced over MCP instead of defined
locally in the calling code.
"""

from mcp.server.fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt()
    def explain_concept(topic: str) -> str:
        """Explain a LangChain/LangGraph concept simply, with a short example."""
        return (
            f"Explain the concept of '{topic}' as it applies to building LLM "
            "applications with LangChain or LangGraph. Keep it to 3-4 sentences, "
            "written for someone new to the topic, and include one short concrete "
            "example."
        )
