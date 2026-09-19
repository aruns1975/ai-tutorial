"""
Customizable chat-history backend for the LangGraph RAG concept.

Mirrors langchain_demo/memory_conversation.py's MemoryBackend selector,
but this module's public functions (get_turns/append_turn) work in plain
HistoryTurn dicts (role/content) rather than BaseChatMessageHistory
objects, since that's the shape sub_graphs/query_rewriter.py's state
expects.

- memory   -> memory_store.py, a fresh in-process closure.
- redis    -> redis_store.py, delegating to
              langchain_demo.memory_conversation_redis.
- postgres -> postgres_store.py, delegating to
              langchain_demo.memory_conversation_postgres.

All three backends implement LangChain's BaseChatMessageHistory
interface (.messages, .add_user_message, .add_ai_message, .clear()), so
get_turns/append_turn work identically regardless of backend — only the
get_history(session_id) provider differs per backend.
"""

from enum import Enum

from langgraph_demo.rag.history_stores import memory_store, postgres_store, redis_store
from langgraph_demo.rag.state import HistoryTurn


class HistoryBackend(str, Enum):
    memory = "memory"
    redis = "redis"
    postgres = "postgres"


_PROVIDERS = {
    HistoryBackend.memory: memory_store.get_history,
    HistoryBackend.redis: redis_store.get_history,
    HistoryBackend.postgres: postgres_store.get_history,
}


def get_turns(session_id: str, backend: HistoryBackend) -> list[HistoryTurn]:
    """Return a session's prior turns as [{"role": "human"|"ai", "content": str}, ...]."""
    history = _PROVIDERS[backend](session_id)
    return [{"role": m.type, "content": m.content} for m in history.messages]


def append_turn(session_id: str, backend: HistoryBackend, question: str, answer: str) -> None:
    """Record one question/answer exchange onto a session's history."""
    history = _PROVIDERS[backend](session_id)
    history.add_user_message(question)
    history.add_ai_message(answer)
