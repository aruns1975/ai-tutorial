# Agents (ReAct-style, tool-using loops)

> 🧪 **Try it hands-on:** [`jupyter/06-react-agents.ipynb`](jupyter/06-react-agents.ipynb) — build this concept from scratch, cell by cell, with a Playground section to experiment in.

## Concept

An agent is a loop: the model reasons about what to do, optionally calls a
tool, observes the result, and repeats until it has enough information to
answer. This is the ReAct pattern (Reason + Act). Contrast with
`tool_calling.py` (concept 3), which does exactly one round of "call a tool,
then answer" — an agent can chain several tool calls before producing a
final answer.

This concept also demonstrates **LangGraph's native persistence**: a
`checkpointer` attached to the compiled graph gives the agent multi-turn
memory keyed by a `thread_id` — LangGraph's own answer to the same
problem the Memory concept solves with `RunnableWithMessageHistory`
(which is deprecated upstream specifically in favor of this). Selected
via `memory_backend`, the same three options as the Memory concept.

## Code walkthrough

See `langchain_demo/react_agent.py`, plus
`langchain_demo/react_agent_redis.py` and
`langchain_demo/react_agent_postgres.py` for the two persistent backends.

### Closure vs. a bare module-level dict

The compiled-agent cache is built by a factory function returning a
closure, the same pattern used in `memory_conversation.py`:

```python
def create_agent_cache():
    agents: dict[tuple[SupportedModel, AgentMemoryBackend], object] = {}

    def get_agent(model, memory_backend):
        key = (model, memory_backend)
        if key not in agents:
            checkpointer = _CHECKPOINTER_BUILDERS[memory_backend]()
            agents[key] = create_react_agent(
                get_chat_model(model), tools=_AGENT_TOOLS, checkpointer=checkpointer, prompt=AGENT_SYSTEM_PROMPT
            )
        return agents[key]

    return get_agent

_get_agent = create_agent_cache()
```

### `AGENT_SYSTEM_PROMPT` — stopping a tool-call repeat loop

```python
AGENT_SYSTEM_PROMPT = (
    "You are a helpful assistant with access to tools. Once a tool call has "
    "returned a result that answers the user's question, respond directly "
    "with the final answer in plain text. Never call the same tool with the "
    "same arguments more than once."
)
```

Without this, `gemma4` was observed to re-call a tool with **identical**
arguments over a dozen times after already getting the correct result,
before finally emitting a plain-text final message — `create_react_agent`'s
default ReAct loop has no built-in "stop once you have the answer"
instruction, and a smaller model doesn't reliably infer it on its own. See
Gotchas below for the exact reproduction. `llama3.2` didn't need this
prompt, but it's harmless for it too. `run_agent_demo` also passes an
explicit `recursion_limit=15` (instead of LangGraph's default 25) as a
backstop, so a genuine runaway case fails fast with a clear error instead
of quietly grinding through many more rounds.

The file's source has a full comment block contrasting this with a bare
module-level `_agents` dict (what this file used to look like, before
checkpointers) — same behavior, but the closure makes it impossible for
unrelated code to reach the cache directly. See
`docs/langchain/05-memory-conversation.md` for the fuller write-up of this
same trade-off.

### Checkpointer backends

```python
_CHECKPOINTER_BUILDERS = {
    AgentMemoryBackend.memory: InMemorySaver,
    AgentMemoryBackend.redis: react_agent_redis.build_checkpointer,
    AgentMemoryBackend.postgres: react_agent_postgres.build_checkpointer,
}
```

- **memory** — `langgraph.checkpoint.memory.InMemorySaver`, no setup
  needed, lost on restart.
- **redis** — `react_agent_redis.py`'s `RedisSaver`, backed by the same
  local Redis instance the RAG/Memory concepts use.
- **postgres** — `react_agent_postgres.py`'s `PostgresSaver`, connecting
  as the same least-privilege `POSTGRES_APP_USER` the RAG/Memory concepts
  use. Verified to survive a full app restart.

### `session_id` == LangGraph's `thread_id`

```python
def run_agent_demo(user_message, model=SupportedModel.llama3_2, memory_backend=AgentMemoryBackend.memory, session_id=None):
    agent = _get_agent(model, memory_backend)
    thread_id = session_id or str(uuid.uuid4())
    result = agent.invoke({"messages": [("human", user_message)]}, config={"configurable": {"thread_id": thread_id}})
    ...
```

Omit `session_id` for the original single-shot behavior (a fresh,
never-reused thread is generated and discarded — fully backward
compatible with earlier examples in this repo). Pass the same
`session_id` across calls to get multi-turn agent memory — in that case
`steps` reflects the **entire thread's accumulated history**, not just
the current turn, since LangGraph merges each call's messages into
persisted state.

## Choosing a model, backend, and session

Accepts three optional **query parameters**:
- `model`: `"llama3.2"` (default) or `"gemma4"`.
- `memory_backend`: `"memory"` (default), `"redis"`, or `"postgres"`.
- `session_id`: any string; omit for stateless single-shot calls.

## Local infra prerequisites

None for `memory_backend=memory` (the default). `redis`/`postgres` need
`scripts/start_infra.sh` — same infra the RAG/Memory concepts use.

## How to call it

```bash
curl -s -X POST localhost:18282/langchain/agents \
  -H 'Content-Type: application/json' \
  -d '{"message": "How many days are between 2026-01-01 and 2026-03-15?"}'

curl -s -X POST "localhost:18282/langchain/agents?model=gemma4" \
  -H 'Content-Type: application/json' \
  -d '{"message": "How many days are between 2026-01-01 and 2026-03-15?"}'

# multi-turn agent memory, backed by Postgres, surviving app restarts
curl -s -X POST "localhost:18282/langchain/agents?memory_backend=postgres&session_id=demo-thread" \
  -H 'Content-Type: application/json' -d '{"message": "My favorite number is 42."}'
curl -s -X POST "localhost:18282/langchain/agents?memory_backend=postgres&session_id=demo-thread" \
  -H 'Content-Type: application/json' -d '{"message": "What is my favorite number?"}'
```

## Gotchas

- Small local models can struggle to chain *multiple* tool calls in one
  request. Feeding "Add 15 and 27, then multiply the result by 2" produces
  a `tool_call` for `multiplier(15, 27)` (wrong tool for step one, and the
  result — 405 — is itself wrong for what was asked), and then the
  **final answer ignores that result entirely**, inventing "42" and "84"
  from nowhere. The `steps` trace and the `final_answer` can genuinely
  diverge — always check `steps` when debugging an agent, don't trust
  `final_answer` alone. Single-tool-call requests, like the example above,
  work reliably. See `docs/TESTING.md` §6b for the full captured example.
  This is a model-capability limitation, not a bug in the agent wiring — a
  larger model handles multi-step tool chaining more reliably.
- Without `session_id`, every call gets a brand-new `thread_id` — the
  checkpointer still writes a (never-reused) row/key for it, so choosing
  `redis`/`postgres` without ever passing `session_id` still does I/O per
  call, it just never accumulates visible history. Pass `session_id` to
  actually see the persistence.
- **A correct `session_id` is not enough to prevent a tool-call repeat
  loop on its own** — verified live with gemma4: `session_id=ses123`,
  "what is 3+4?" then "what happens when I add 5 to it?". The agent
  correctly recalled the previous result (7) and correctly computed
  `adder(7, 5) = 12` on its *first* attempt, then called the exact same
  `adder(7, 5)` again — and again, ~14 times total — before finally
  responding with plain text `"12"`. `AGENT_SYSTEM_PROMPT` (above) is
  the actual fix; reproduced clean (one `adder` call per turn) across 3
  separate sessions after adding it. Don't re-diagnose a report like
  this as a memory/session bug without checking `steps` first — the
  giveaway is a tool called with **identical** args more than once in a
  row after the correct result already appeared.
