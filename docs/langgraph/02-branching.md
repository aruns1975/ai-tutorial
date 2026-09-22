# Conditional Edges / Branching

> 🧪 **Try it hands-on:** [`jupyter/02-branching.ipynb`](jupyter/02-branching.ipynb) — build this concept from scratch, cell by cell, with a Playground section to experiment in.

## Concept

`add_conditional_edges` routes execution to a different node based on the
current state, instead of following a single fixed edge. Demonstrated
with a small router: classify a question as "math" or "general", then
send it to the node specialized for that category.

## Code walkthrough

See `langgraph_demo/branching.py`. The router function reads state and
returns the name of the next node to run:

```python
def route(state: RouterState) -> Literal["solve_math", "answer_general"]:
    return "solve_math" if state["category"] == "math" else "answer_general"

graph.add_node("classify", classify)
graph.add_node("solve_math", solve_math)
graph.add_node("answer_general", answer_general)
graph.add_edge(START, "classify")
graph.add_conditional_edges("classify", route)
graph.add_edge("solve_math", END)
graph.add_edge("answer_general", END)
```

`solve_math` reuses `tools/math_tools.py` via `llm.bind_tools(...)` and
`langchain_demo.tool_utils.create_tool_caller` — the exact same
tool-execution pattern as `langchain_demo/tool_calling.py`, just invoked
from inside a graph node instead of a plain function.

## Choosing a model

Accepts an optional `model` **query parameter** (`?model=...`):
`"llama3.2"` (default) or `"gemma4"`.

## Local infra prerequisites

None.

## How to call it

```bash
curl -s -X POST localhost:18282/langgraph/branching \
  -H 'Content-Type: application/json' -d '{"question": "What is 9 times 8?"}'

curl -s -X POST localhost:18282/langgraph/branching \
  -H 'Content-Type: application/json' -d '{"question": "What is the tallest mountain?"}'
```

## Gotchas

- The `classify` node's category is decided by a *separate* LLM call from
  `solve_math`/`answer_general`'s actual work — a genuinely ambiguous
  question can be classified into the "wrong" branch (e.g. a word problem
  that's actually asking a math question but doesn't say the word "math").
  This is the same small-model classification unreliability documented
  elsewhere in this project, not a bug in the routing logic itself.
