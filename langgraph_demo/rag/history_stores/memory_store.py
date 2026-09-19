"""
In-memory chat history for the LangGraph RAG concept's `memory`
history_backend.

Unlike the redis/postgres siblings in this submodule (which delegate to
langchain_demo's already-debugged backends — see those files' docstrings),
a plain per-session dict is cheap and bug-free enough that writing it
fresh here costs less than adding an import indirection to
langchain_demo.memory_conversation's private store. Same closure pattern
as that module's create_memory_history_store(), though: the dict lives
only inside create_history_cache()'s local scope.
"""

from langchain_core.chat_history import InMemoryChatMessageHistory


def create_history_cache():
    """Return a get_history(session_id) closure over a private per-session dict."""
    store: dict[str, InMemoryChatMessageHistory] = {}

    def get_history(session_id: str) -> InMemoryChatMessageHistory:
        return store.setdefault(session_id, InMemoryChatMessageHistory())

    return get_history


get_history = create_history_cache()
