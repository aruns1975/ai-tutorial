"""
Concept: Memory / conversation history.

Demonstrates multi-turn conversation using RunnableWithMessageHistory,
backed by one of three interchangeable message-history stores selected
via `memory_backend`:

- memory   -> a process-local dict, encapsulated in a closure (see
              create_memory_history_store() below). Lost on restart, not
              shared across app instances.
- redis    -> langchain_demo/memory_conversation_redis.py, backed by the
              same local Redis instance the RAG concept's "redis" backend
              uses.
- postgres -> langchain_demo/memory_conversation_postgres.py, backed by
              the same local Postgres instance (least-privilege app user)
              the RAG concept's "postgres" backend uses.

All three implement LangChain's BaseChatMessageHistory interface
(`.messages`, `.clear()`), so run_conversation_turn/
get_conversation_history/clear_conversation work identically regardless
of backend — only the `get_history(session_id) -> BaseChatMessageHistory`
provider differs per backend.
"""

from enum import Enum

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from langchain_demo import memory_conversation_postgres, memory_conversation_redis
from models.chat_models.ollama_models import SupportedModel, get_chat_model


class MemoryBackend(str, Enum):
    memory = "memory"
    redis = "redis"
    postgres = "postgres"


# -----------------------------------------------------------------------
# Encapsulation: closure vs. a bare module-level dict
#
# WITHOUT a closure, the in-memory session store would just be a
# module-level dict that every function in this file reads and writes
# directly:
#
#     _HISTORY_STORE: dict[str, InMemoryChatMessageHistory] = {}
#
#     def _get_memory_history(session_id: str) -> InMemoryChatMessageHistory:
#         return _HISTORY_STORE.setdefault(session_id, InMemoryChatMessageHistory())
#
# This works fine — it's exactly what this file used to do — but
# `_HISTORY_STORE` is a name any function in this module (today, or added
# next month) can reach in and mutate directly. Nothing enforces that only
# the intended code path touches it; the boundary is "please don't",
# not "can't".
#
# WITH a closure (the active implementation just below), the dict lives
# only inside create_memory_history_store()'s local scope. The function it
# returns is the ONLY way to reach that dict — no other name anywhere in
# this module refers to it, so it is not just discouraged but IMPOSSIBLE
# for unrelated code to mutate it directly. Same behavior, a strictly
# stronger boundary. This is the same trade-off already used elsewhere in
# this project: tool_utils.create_tool_caller and
# model_utils.fetch_all_models both build a private lookup once and hand
# back a closure as the only access point.
# -----------------------------------------------------------------------

def create_memory_history_store():
    """
    Build an in-memory session history store. Returns a get_history(session_id)
    closure — the only way to reach the private dict inside this function.
    """
    store: dict[str, InMemoryChatMessageHistory] = {}

    def get_history(session_id: str) -> InMemoryChatMessageHistory:
        return store.setdefault(session_id, InMemoryChatMessageHistory())

    return get_history


_get_memory_history = create_memory_history_store()

# A plain dict, not another closure, is the right tool here: this registry
# is a static lookup table built once at import time, not mutable state
# that needs protecting — wrapping it in a closure would add indirection
# with no encapsulation benefit. Know when a closure earns its keep (the
# store above) versus when it doesn't (this registry).
_HISTORY_PROVIDERS = {
    MemoryBackend.memory: _get_memory_history,
    MemoryBackend.redis: memory_conversation_redis.get_history,
    MemoryBackend.postgres: memory_conversation_postgres.get_history,
}

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful assistant with a good memory for the current conversation."),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)


def run_conversation_turn(
    session_id: str,
    message: str,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: MemoryBackend = MemoryBackend.memory,
) -> dict:
    """
    Run one turn of a multi-turn conversation for the given session and
    backend, appending to that session's history. `model` only affects
    this turn's response — history itself is model-agnostic, so switching
    models mid-conversation is possible.

    Returns {"session_id": str, "backend": str, "response": str, "turn_count": int}.
    """
    llm = get_chat_model(model)
    get_history = _HISTORY_PROVIDERS[memory_backend]
    chain_with_history = RunnableWithMessageHistory(
        _prompt | llm,
        get_history,
        input_messages_key="input",
        history_messages_key="history",
    )
    response = chain_with_history.invoke(
        {"input": message},
        config={"configurable": {"session_id": session_id}},
    )
    turn_count = sum(1 for m in get_history(session_id).messages if m.type == "human")
    return {
        "session_id": session_id,
        "backend": memory_backend.value,
        "response": response.content,
        "turn_count": turn_count,
    }


def get_conversation_history(session_id: str, memory_backend: MemoryBackend = MemoryBackend.memory) -> list[dict]:
    """
    Return [{"role": "human"|"ai", "content": str}, ...] for a session on
    the given backend, or [] if the session doesn't exist yet.
    """
    get_history = _HISTORY_PROVIDERS[memory_backend]
    return [{"role": m.type, "content": m.content} for m in get_history(session_id).messages]


def clear_conversation(session_id: str, memory_backend: MemoryBackend = MemoryBackend.memory) -> bool:
    """Delete a session's history on the given backend. Returns whether it had any messages."""
    get_history = _HISTORY_PROVIDERS[memory_backend]
    history = get_history(session_id)
    had_messages = bool(history.messages)
    history.clear()
    return had_messages
