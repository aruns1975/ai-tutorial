"""
Postgres-backed chat history for the LangGraph RAG concept's `postgres`
history_backend.

Thin delegate to langchain_demo.memory_conversation_postgres, which
already solved the UUID-typed session_id column mismatch (via
uuid.uuid5 hashing) and owns the table's connection/provisioning — see
that module's docstring. Both concepts' postgres-backed history end up
in the same ai_tutorial_chat_history table, so a session started via
/langchain/memory and continued via /langgraph/rag shares history.
"""

from langchain_demo.memory_conversation_postgres import get_history

__all__ = ["get_history"]
