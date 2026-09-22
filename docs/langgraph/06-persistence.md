# Persistence / Checkpointers (Standalone)

> 🧪 **Try it hands-on:** [`jupyter/06-persistence.ipynb`](jupyter/06-persistence.ipynb) — build this concept from scratch, cell by cell, with a Playground section to experiment in.

## Concept

Contrast with `langchain_demo/react_agent.py`: that demo shows a
*prebuilt* agent gaining memory when you hand `create_react_agent` a
checkpointer. This one shows the same mechanic on a completely plain,
hand-written `StateGraph` with no LLM and no tools at all — a
checkpointer is a property of the *graph*, not something special about
agents. Any `StateGraph` gets persistent, resumable state across separate
`.invoke()` calls just by compiling it with `checkpointer=...` and
reusing the same `thread_id`.

## Code walkthrough

See `langgraph_demo/persistence.py`. A trivial counter graph: each call
increments a count and appends to a history list.

```python
def _increment(state: CounterState) -> dict:
    count = state.get("count", 0) + 1
    history = state.get("history", []) + [f"incremented to {count}"]
    return {"count": count, "history": history}

compiled = graph.compile(checkpointer=build_checkpointer(memory_backend))
```

`run_persistence_demo` invokes with an **empty dict**, not
`{"count": 0, ...}` — passing an explicit `count` would overwrite the
checkpointed value back to zero on every call instead of accumulating.
`.get("count", 0)` inside the node supplies the default only when no
checkpoint exists yet (a brand-new `thread_id`).

Uses `langgraph_demo/checkpointers.py`'s shared builders — the same
`memory`/`redis`/`postgres` choice as `interrupts.py`.

## Choosing a backend

Accepts `memory_backend` (`"memory"` default, `"redis"`, or `"postgres"`)
as a **query parameter**. No `model` — this graph never calls an LLM.

## Local infra prerequisites

None for `memory_backend=memory` (the default). `redis`/`postgres` need
`scripts/start_infra.sh`.

## How to call it

```bash
curl -s -X POST localhost:18282/langgraph/persistence/demo-counter
curl -s -X POST localhost:18282/langgraph/persistence/demo-counter   # count: 2

# persists across an app restart
curl -s -X POST "localhost:18282/langgraph/persistence/demo-counter?memory_backend=postgres"
scripts/stop_app.sh && scripts/start_app.sh
curl -s -X POST "localhost:18282/langgraph/persistence/demo-counter?memory_backend=postgres"   # continues counting, doesn't reset
```

## Gotchas

- Only `memory_backend=memory` resets on restart, by design — `redis`/
  `postgres` were verified to survive a full `scripts/stop_app.sh &&
  scripts/start_app.sh` restart and continue counting from where they
  left off.
- Different `session_id` (path param) values are fully isolated — each
  gets its own independent counter.
