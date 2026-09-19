"""
Redis-backed chat history for the LangGraph RAG concept's `redis`
history_backend.

Thin delegate to langchain_demo.memory_conversation_redis, which already
solved the langchain_redis 0.2.5 overwrite_index bug and the per-session
reindex race (see that module's docstring) — re-deriving that fix here
would just be duplicated bug surface, not a simpler implementation. Both
concepts' redis-backed history end up in the same Redis instance, keyed
by session_id under the same key prefix, so a session started via
/langchain/memory and continued via /langgraph/rag shares history.
"""

from langchain_demo.memory_conversation_redis import get_history

__all__ = ["get_history"]
