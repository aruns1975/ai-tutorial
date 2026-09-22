# Streaming Graph Execution

> 🧪 **Try it hands-on:** [`jupyter/04-streaming-graph.ipynb`](jupyter/04-streaming-graph.ipynb) — build this concept from scratch, cell by cell, with a Playground section to experiment in.

## Concept

Contrast with `langchain_demo/streaming_demo.py`: that streams individual
*tokens* from one model call, character by character. A graph's
`.astream(stream_mode="updates")` streams one event *per node* as it
finishes — you watch the graph's control flow execute step by step, not
the text of any single response appear incrementally.

## Code walkthrough

See `langgraph_demo/streaming_graph.py`. It deliberately reuses
`stategraph_basics.py`'s exact fact → joke graph (via the exported
`get_fact_joke_graph`), so the two streaming styles can be compared
against identical underlying work:

```python
async def stream_stategraph_demo(topic, model=SupportedModel.llama3_2):
    graph = get_fact_joke_graph(model)
    async for update in graph.astream({"topic": topic, "fact": "", "joke": ""}, stream_mode="updates"):
        for node_name, output in update.items():
            yield {"node": node_name, "output": output}
```

`controllers/langgraph_streaming_controller.py` wraps this in the same
FastAPI SSE pattern as `streaming_controller.py`, JSON-encoding each
`{"node": ..., "output": ...}` event as one `data:` line.

## Choosing a model

Accepts an optional `model` **query parameter** (`?model=...`):
`"llama3.2"` (default) or `"gemma4"`.

## Local infra prerequisites

None.

## How to call it

```bash
curl -N -X POST localhost:18282/langgraph/streaming \
  -H 'Content-Type: application/json' -d '{"topic": "penguins"}'
```

You'll see exactly two `data:` lines (one per node) instead of dozens of
token-by-token chunks — compare against
`curl -N -X POST localhost:18282/langchain/streaming -d '{"topic": "penguins"}'`
side by side.

## Gotchas

- Each event's `output` is the *whole* node's return value (e.g. the
  entire generated fact/joke text), not sub-chunks of it — `stream_mode="updates"`
  streams at node granularity, not token granularity. Use
  `stream_mode="messages"` (not demonstrated here) if you want both node
  boundaries *and* token-level streaming within LLM-calling nodes.
