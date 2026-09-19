# Human-in-the-Loop / Interrupts

## Concept

`interrupt()` pauses a graph mid-node and surfaces a value to the caller;
the caller resumes execution later with `Command(resume=...)`. This is a
distinctly LangGraph feature with no equivalent anywhere in the
LangChain concepts in this project — a chain either finishes or it
doesn't, but a graph can pause indefinitely awaiting a human decision.
Interrupts require a checkpointer, since the paused state has to be
persisted somewhere between the pausing call and the resuming call.

## Code walkthrough

See `langgraph_demo/interrupts.py`. A draft → request_approval → finalize
graph: draft a short reply, pause for a human approve/reject decision,
then finalize accordingly.

```python
def request_approval(state: ApprovalState) -> dict:
    decision = interrupt({"question": "Approve this draft?", "draft": state["draft"]})
    return {"approved": bool(decision)}

compiled = graph.compile(checkpointer=build_checkpointer(memory_backend))
```

Two entry points, since a paused graph needs a way to start and a
separate way to resume:

```python
def start_approval_demo(request, session_id, model, memory_backend):
    result = graph.invoke({"request": request, ...}, config={"configurable": {"thread_id": session_id}})
    interrupt_payload = result["__interrupt__"][0].value   # what interrupt() surfaced
    return {"status": "waiting_for_approval", "draft": interrupt_payload["draft"]}

def resume_approval_demo(session_id, approved, model, memory_backend):
    result = graph.invoke(Command(resume=approved), config={"configurable": {"thread_id": session_id}})
    return {"status": "done", "result": result["result"]}
```

Backed by `langgraph_demo/checkpointers.py`'s shared builders — the same
`memory`/`redis`/`postgres` choice as `persistence.py`.

## Choosing a model, backend, and session

Accepts `model` (`"llama3.2"` default or `"gemma4"`) and `memory_backend`
(`"memory"` default, `"redis"`, or `"postgres"`) as **query parameters**.
`session_id` is a required **body** field on both `/start` and `/resume`
— it's how the resume call finds the paused state to continue.

## Local infra prerequisites

None for `memory_backend=memory` (the default). `redis`/`postgres` need
`scripts/start_infra.sh`.

## How to call it

```bash
curl -s -X POST localhost:18282/langgraph/interrupts/start \
  -H 'Content-Type: application/json' \
  -d '{"request": "Can you extend my deadline by two days?", "session_id": "approval-1"}'

# approve
curl -s -X POST localhost:18282/langgraph/interrupts/resume \
  -H 'Content-Type: application/json' -d '{"session_id": "approval-1", "approved": true}'

# or reject a different session
curl -s -X POST localhost:18282/langgraph/interrupts/start \
  -H 'Content-Type: application/json' \
  -d '{"request": "Cancel my subscription immediately.", "session_id": "approval-2"}'
curl -s -X POST localhost:18282/langgraph/interrupts/resume \
  -H 'Content-Type: application/json' -d '{"session_id": "approval-2", "approved": false}'
```

## Gotchas

- **`model`/`memory_backend` must match between `/start` and `/resume`
  for `memory_backend=memory`.** The compiled graph (and its
  `InMemorySaver`) is cached per `(model, memory_backend)` pair — calling
  `/resume` with a different `model` than `/start` used fetches a
  *different* cached graph with its own separate in-memory checkpoint
  store, and the paused state won't be found. This doesn't apply to
  `redis`/`postgres`: those checkpoints live in the external store, so
  they're found regardless of which model compiled the graph — but
  matching `model` and `memory_backend` between calls is still the
  correct, unsurprising way to use this endpoint regardless of backend.
- `resume_approval_demo` checks `graph.get_state(config).next` before
  resuming — if there's no pending interrupt for that
  `(session_id, model, memory_backend)` combination (mismatched params,
  a `session_id` that never called `/start`, or one already finished),
  it raises a `ValueError` that the controller turns into a `400` with a
  clear message, instead of the raw `KeyError`/`500` this used to produce.

