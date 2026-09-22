# LCEL Chains (Runnables, pipe syntax)

> 🧪 **Try it hands-on:** [`jupyter/02-lcel-chains.ipynb`](jupyter/02-lcel-chains.ipynb) — build this concept from scratch, cell by cell, with a Playground section to experiment in.

## Concept

LangChain Expression Language (LCEL) lets you compose steps with the `|`
operator, similar to a Unix pipe: `prompt | llm | parser` reads left to
right — format the prompt, send it to the model, parse the result. Every
step is a `Runnable`, and several helper Runnables make more complex
compositions possible:

- `RunnableParallel` — runs multiple branches over the same input at once.
- `RunnableLambda` — lifts a plain Python function into the chain.
- `RunnablePassthrough` — forwards the original input unchanged, useful
  when a later step needs both a derived value and the original input.

## Code walkthrough

See `langchain_demo/lcel_chains.py`.

`run_pipe_chain_demo(text, model=SupportedModel.llama3_2)` is the minimal
case: `prompt | llm | StrOutputParser()`, where `llm = get_chat_model(model)`.

`run_parallel_chain_demo(topic, model=SupportedModel.llama3_2)` fans a
single string out into three branches via `RunnableParallel`:

```python
llm = get_chat_model(model)
parallel_chain = RunnableParallel(
    summary=to_prompt_input | summary_prompt | llm | StrOutputParser(),
    questions=to_prompt_input | questions_prompt | llm | StrOutputParser() | split_lines,
    original_topic=RunnablePassthrough(),
)
```

`to_prompt_input` is a `RunnableLambda` that wraps the plain input string
into the `{"topic": ...}` dict shape the prompts need. `original_topic`
uses `RunnablePassthrough()` to hand the same input string straight through
unchanged, alongside the two LLM-derived branches — all three run
concurrently against the same input.

## Choosing a model

Both endpoints accept an optional `model` **query parameter**
(`?model=...`): `"llama3.2"` (default) or `"gemma4"`.

## Local infra prerequisites

None.

## How to call it

```bash
curl -s -X POST localhost:18282/langchain/chains/pipe \
  -H 'Content-Type: application/json' \
  -d '{"text": "The mitochondria is the powerhouse of the cell."}'

curl -s -X POST localhost:18282/langchain/chains/parallel \
  -H 'Content-Type: application/json' \
  -d '{"topic": "the water cycle"}'

# same as above, against gemma4
curl -s -X POST "localhost:18282/langchain/chains/parallel?model=gemma4" \
  -H 'Content-Type: application/json' \
  -d '{"topic": "the water cycle"}'
```

## Gotchas

- `RunnableParallel` passes the *same* input to every branch — if your
  branches need different input shapes, use a `RunnableLambda` per branch to
  adapt it (as `to_prompt_input` does here), rather than trying to make one
  prompt template's key structure fit every branch.
