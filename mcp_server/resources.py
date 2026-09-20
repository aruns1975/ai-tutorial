"""
Resources exposed by this project's MCP server.

Two examples, chosen to show both resource shapes:

- data://ai-tutorial/rag-corpus — a STATIC file resource: the exact
  same corpus langchain_demo/rag_demo.py ingests for RAG, re-exposed
  as-is (no new content, no duplicated corpus) so an MCP client can
  read the same source document the RAG concept retrieves chunks from.
- data://ai-tutorial/models — a DYNAMIC resource: computed on each
  read from models.chat_models.ollama_models.SupportedModel, so it
  always reflects whichever chat models this project currently
  supports, without hardcoding a second list anywhere.
"""

from mcp.server.fastmcp import FastMCP

from langchain_demo.rag_demo import CORPUS_PATH
from models.chat_models.ollama_models import SupportedModel


def register_resources(mcp: FastMCP) -> None:
    @mcp.resource("data://ai-tutorial/rag-corpus", mime_type="text/markdown")
    def rag_corpus() -> str:
        """The sample corpus langchain_demo/rag_demo.py ingests for RAG."""
        return CORPUS_PATH.read_text()

    @mcp.resource("data://ai-tutorial/models")
    def supported_models() -> list[str]:
        """The chat model tags this project currently supports."""
        return [model.value for model in SupportedModel]
