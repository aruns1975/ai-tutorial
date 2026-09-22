# Cycles / Loops

> 🧪 **Try it hands-on:** [`jupyter/03-cycles.ipynb`](jupyter/03-cycles.ipynb) — build this concept from scratch, cell by cell, with a Playground section to experiment in.

## Concept

A graph edge can point back to a node that already ran — LangGraph
doesn't require a DAG. Demonstrated with a retry loop: ask the model for
a topic description within a word limit, and if the response comes back
too long, loop back and ask again (feeding back *why* the previous
attempt failed), up to `max_attempts`.

Contrast with `branching.py`: that graph's conditional edge always
reaches `END` after one specialist node runs. This one's conditional edge
can send execution back to a node already visited — the actual "cycle" a
cyclic graph is named for.

## Code walkthrough

See `langgraph_demo/cycles.py`:

```python
def should_continue(state: RefineState) -> Literal["generate", "__end__"]:
    if state["word_count"] <= state["max_words"] or state["attempt"] >= state["max_attempts"]:
        return END
    return "generate"

graph.add_node("generate", generate)
graph.add_edge(START, "generate")
graph.add_conditional_edges("generate", should_continue)
```

`generate` includes the previous attempt's text and word count in its
prompt on retries — feeding back *why* the last attempt failed, not just
asking again blindly. This matters in practice: a naive "just try again"
retry with no feedback rarely converges, since the model doesn't know
what to change.

## Choosing a model

Accepts an optional `model` **query parameter** (`?model=...`):
`"llama3.2"` (default) or `"gemma4"`.

## Local infra prerequisites

None.

## How to call it

```bash
curl -s -X POST localhost:18282/langgraph/cycles \
  -H 'Content-Type: application/json' \
  -d '{"topic": "a dog", "max_words": 5, "max_attempts": 4}'
```

## Gotchas

- With the word limit stated up front in the prompt, `llama3.2` usually
  meets it on the *first* attempt (`attempts_used: 1`) — the loop is a
  safety net, not something you'll normally see fire. To actually watch
  it retry, try an unreasonably tight `max_words` (e.g. `1`) against a
  topic that's genuinely hard to compress, or lower `max_attempts` to see
  `met_target: false` when it runs out of tries.
- `max_attempts` is a hard cap — if the model never converges, the graph
  still terminates (via `should_continue`'s second condition) rather than
  looping forever. Always set a `max_attempts` on any retry-style cycle
  you build; an unconditional loop-back edge would spin indefinitely.
