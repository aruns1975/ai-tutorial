# Memory / Conversation History

## Concept

Chat models are stateless: each call only sees what you send it. To hold a
multi-turn conversation, the message history has to be tracked outside the
model and re-sent on every turn. `RunnableWithMessageHistory` automates
this — given a session id, it looks up that session's history, injects it
into the prompt, invokes the model, and appends the new exchange back into
history.

This concept also demonstrates **three interchangeable history stores**,
selected via `memory_backend`, all implementing LangChain's
`BaseChatMessageHistory` interface (`.messages`, `.clear()`) — the same
"pick a backend, same behavior" idea as the RAG concept's vector stores.

## Code walkthrough

See `langchain_demo/memory_conversation.py`, plus
`langchain_demo/memory_conversation_redis.py` and
`langchain_demo/memory_conversation_postgres.py` for the two additional
backends.

### Closure vs. a bare module-level dict

The in-memory backend's session store is built by a factory function
returning a closure, rather than a plain module-level dict:

```python
def create_memory_history_store():
    store: dict[str, InMemoryChatMessageHistory] = {}

    def get_history(session_id: str) -> InMemoryChatMessageHistory:
        return store.setdefault(session_id, InMemoryChatMessageHistory())

    return get_history

_get_memory_history = create_memory_history_store()
```

The file's source has a full comment block contrasting this with the
equivalent **without** a closure (a bare `_HISTORY_STORE` dict + a
function reading/writing it directly — what this file used to look like)
— both versions do the same thing; the closure version just makes it
*impossible* for unrelated code elsewhere in the module to reach in and
mutate the store directly, rather than merely discouraged. Read that
comment block for the full side-by-side.

Not everything needs a closure, though: `_HISTORY_PROVIDERS` (the
`{backend: get_history_function}` registry below) is a plain dict, not
another closure — it's a static lookup table built once, not mutable
state that needs protecting. Knowing when a closure earns its keep
(the store) versus when it's just indirection (the registry) is the other
half of the lesson.

### Backend dispatch

```python
_HISTORY_PROVIDERS = {
    MemoryBackend.memory: _get_memory_history,
    MemoryBackend.redis: memory_conversation_redis.get_history,
    MemoryBackend.postgres: memory_conversation_postgres.get_history,
}

def run_conversation_turn(session_id, message, model=SupportedModel.llama3_2, memory_backend=MemoryBackend.memory):
    llm = get_chat_model(model)
    get_history = _HISTORY_PROVIDERS[memory_backend]
    chain_with_history = RunnableWithMessageHistory(_prompt | llm, get_history, ...)
    ...
```

Because every backend's `get_history(session_id)` returns something with
`.messages`/`.clear()`, `run_conversation_turn`,
`get_conversation_history`, and `clear_conversation` contain **no
backend-specific branching** at all — only the provider function differs.

### The other two backends

- **Redis** (`memory_conversation_redis.py`) — uses
  `langchain_redis.RedisChatMessageHistory`. Also uses a closure, but for
  a different reason than the in-memory store: Redis itself holds the
  data, but constructing `RedisChatMessageHistory` re-declares its search
  index every time, and doing that on every call raced a reindex and
  returned incomplete history. `create_history_cache()` caches one
  instance per `session_id` so that only happens once per session. See
  that file's docstring for the full explanation, including a
  `langchain_redis` library bug this works around.
- **Postgres** (`memory_conversation_postgres.py`) — uses
  `langchain_postgres.PostgresChatMessageHistory`, connecting as the same
  least-privilege `POSTGRES_APP_USER` the RAG postgres backend uses.
  Session ids are hashed to a stable UUID first (the backing table's
  `session_id` column is typed `UUID`, but this concept accepts arbitrary
  string session ids).

## Choosing a model and backend

`POST /langchain/memory/{session_id}` accepts two optional **query
parameters**: `model` (`"llama3.2"` default or `"gemma4"`) and
`memory_backend` (`"memory"` default, `"redis"`, or `"postgres"`). Since
history itself is model-agnostic, you can switch models *mid-conversation*
— the new model simply sees the same accumulated history. `GET`/`DELETE`
also accept `memory_backend` (they don't need `model` — reading/clearing
doesn't call the LLM).

## Local infra prerequisites

None for `memory_backend=memory` (the default). `redis`/`postgres` need
`scripts/start_infra.sh` — same infra the RAG concept uses.

## How to call it

```bash
curl -s -X POST localhost:18282/langchain/memory/demo-session \
  -H 'Content-Type: application/json' -d '{"message": "my name is Arun"}'

# switch to gemma4 for this turn — it still sees the history above
curl -s -X POST "localhost:18282/langchain/memory/demo-session?model=gemma4" \
  -H 'Content-Type: application/json' -d '{"message": "what is my name?"}'

curl -s localhost:18282/langchain/memory/demo-session

curl -s -X DELETE localhost:18282/langchain/memory/demo-session

# same conversation, but backed by Redis instead of the in-process dict
curl -s -X POST "localhost:18282/langchain/memory/demo-session?memory_backend=redis" \
  -H 'Content-Type: application/json' -d '{"message": "my name is Arun"}'
curl -s "localhost:18282/langchain/memory/demo-session?memory_backend=redis"

# same again, backed by Postgres
curl -s -X POST "localhost:18282/langchain/memory/demo-session?memory_backend=postgres" \
  -H 'Content-Type: application/json' -d '{"message": "my name is Arun"}'
curl -s "localhost:18282/langchain/memory/demo-session?memory_backend=postgres"
```

## Gotchas

- **`memory` backend limitation**: history lives in a process-local dict.
  It is lost on app restart and not shared across multiple app instances
  — use `redis` or `postgres` if you need persistence across restarts.
- `RunnableWithMessageHistory` itself is flagged as deprecated upstream in
  favor of LangGraph's built-in persistence (checkpointers). It's used here
  deliberately as the simplest way to demonstrate the *concept* of
  history-augmented chains without introducing a graph; a LangGraph-based
  agent with persistence would be a natural follow-up demo.
- `GET`/`DELETE` on an unknown `session_id` return `404`, regardless of
  backend.
- **Redis backend**: `memory_conversation_redis.py` works around a real
  bug in the installed `langchain_redis==0.2.5` — constructing
  `RedisChatMessageHistory` when its search index already exists crashes
  with `AttributeError: 'dict' object has no attribute 'index'` unless
  `overwrite_index=True` is passed. See that file for the full note and
  why per-session caching (not just the flag) was also needed to avoid a
  reindex race that otherwise returned an incomplete message list.
- **Postgres backend**: session ids are hashed with
  `uuid.uuid5(uuid.NAMESPACE_URL, session_id)` before use, since the
  backing table's `session_id` column is `UUID`-typed. A single shared
  `psycopg` connection is reused across calls rather than a connection
  pool — fine for this demo's traffic, not safe under heavy concurrent
  load (a production version would use `psycopg_pool`).
