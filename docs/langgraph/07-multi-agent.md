# Multi-Agent / Subgraphs

> 🧪 **Try it hands-on:** [`jupyter/07-multi-agent.ipynb`](jupyter/07-multi-agent.ipynb) — build this concept from scratch, cell by cell, with a Playground section to experiment in.

## Concept

A compiled `StateGraph` can be used directly as a node in another
graph — a "subgraph". This is what a multi-agent system actually is in
LangGraph: each specialist agent is its own independently-built,
independently-testable graph; a supervisor graph routes to whichever
specialist fits the request and treats it as a single node.

Contrast with `branching.py`: that demo's specialist logic is a single
plain function per branch. Here, each specialist (`math_specialist`,
`writing_specialist`) is its own fully compiled `StateGraph` — you could
run/test either one in isolation before ever wiring it into the
supervisor.

## Code walkthrough

See `langgraph_demo/multi_agent.py`:

```python
def _build_supervisor_graph(model):
    math_specialist = _build_math_specialist(model)       # its own compiled graph
    writing_specialist = _build_writing_specialist(model)  # its own compiled graph

    graph = StateGraph(SupervisorState)
    graph.add_node("classify", classify)
    graph.add_node("math_specialist", math_specialist)     # a compiled graph, used AS a node
    graph.add_node("writing_specialist", writing_specialist)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", route)
    graph.add_edge("math_specialist", END)
    graph.add_edge("writing_specialist", END)
    return graph.compile()
```

Both specialist graphs share the same `SupervisorState` `TypedDict` as
the parent graph, which is what makes them usable as nodes directly — the
subgraph's state schema needs to be compatible with the parent's for its
output to merge back in cleanly. `math_specialist` reuses
`tools/math_tools.py` via the same `bind_tools` + `create_tool_caller`
pattern as `branching.py`'s `solve_math`.

## Choosing a model

Accepts an optional `model` **query parameter** (`?model=...`):
`"llama3.2"` (default) or `"gemma4"`.

## Local infra prerequisites

None.

## How to call it

```bash
curl -s -X POST localhost:18282/langgraph/multi-agent \
  -H 'Content-Type: application/json' -d '{"request": "What is 100 divided by 4?"}'

curl -s -X POST localhost:18282/langgraph/multi-agent \
  -H 'Content-Type: application/json' -d '{"request": "Write a two-line poem about the moon."}'
```

## Gotchas

- Same classification-reliability caveat as `branching.py`: `classify`
  is a separate LLM call from either specialist's actual work, so a
  genuinely ambiguous request can be routed to the "wrong" specialist.
- Adding a third specialist means: build its own graph (or reuse an
  existing one, e.g. a mini RAG graph), add it as a node, add it to
  `route`'s return type and the classification prompt. The supervisor's
  own structure doesn't otherwise change.
