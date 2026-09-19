# StateGraph Basics

## Concept

The foundational LangGraph building block: a typed state schema, nodes
(plain functions taking the state and returning a partial update), and
edges wiring nodes together into a graph you compile and invoke. Contrast
with `langchain_demo/lcel_chains.py`'s `prompt | llm | parser`: an LCEL
chain is a linear pipe; a `StateGraph` is nodes + edges over a shared,
typed state any node can read or write — which is what makes branching
and cycles possible (see the next two concepts).

## Code walkthrough

See `langgraph_demo/stategraph_basics.py`. A minimal two-node linear
graph: generate a fact about a topic, then generate a joke about that
fact.

```python
class FactJokeState(TypedDict):
    topic: str
    fact: str
    joke: str

graph = StateGraph(FactJokeState)
graph.add_node("generate_fact", generate_fact)
graph.add_node("generate_joke", generate_joke)
graph.add_edge(START, "generate_fact")
graph.add_edge("generate_fact", "generate_joke")
graph.add_edge("generate_joke", END)
compiled = graph.compile()
```

Each node returns only the keys it changes (`{"fact": ...}`) — LangGraph
merges that into the running state rather than requiring the whole state
back. The compiled graph is cached per model via `create_graph_cache()`,
the same closure-factory pattern used throughout this project (see
`langchain_demo/react_agent.py`'s `create_agent_cache()` for the fuller
closure-vs-dict writeup) — `get_fact_joke_graph` is exported (not
underscore-prefixed) specifically so `streaming_graph.py` can reuse this
exact graph.

## Choosing a model

Accepts an optional `model` **query parameter** (`?model=...`):
`"llama3.2"` (default) or `"gemma4"`.

## Local infra prerequisites

None.

## How to call it

```bash
curl -s -X POST localhost:18282/langgraph/stategraph \
  -H 'Content-Type: application/json' -d '{"topic": "black holes"}'
```

## Gotchas

- The two nodes run sequentially, not concurrently — `add_edge` wires a
  strict order. See `branching.py`/`cycles.py` for non-linear control
  flow, and LangChain's `RunnableParallel`
  (`langchain_demo/lcel_chains.py`) for genuinely concurrent branches.
