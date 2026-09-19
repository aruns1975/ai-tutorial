# Streaming

## Concept

Instead of waiting for a model to finish generating a full response, a
chain can stream its output chunk by chunk as it's produced. This lets a
client start displaying a response before generation finishes.

## Code walkthrough

See `langchain_demo/streaming_demo.py`:

```python
async def stream_answer(topic: str, model: SupportedModel = SupportedModel.llama3_2) -> AsyncIterator[str]:
    llm = get_chat_model(model)
    chain = _prompt | llm | StrOutputParser()
    async for chunk in chain.astream({"topic": topic}):
        yield chunk
```

`controllers/streaming_controller.py` wraps this in a FastAPI
`StreamingResponse` using Server-Sent Events (SSE) framing:

```python
async def _sse_events(topic: str, model: SupportedModel):
    async for chunk in stream_answer(topic, model):
        yield f"data: {chunk}\n\n"
    yield "event: done\ndata: [DONE]\n\n"
```

## Choosing a model

Accepts an optional `model` **query parameter** (`?model=...`):
`"llama3.2"` (default) or `"gemma4"` — see the Gotchas section below for a
`gemma4`-specific streaming quirk.

## Local infra prerequisites

None.

## How to call it

```bash
curl -N -X POST localhost:18282/langchain/streaming \
  -H 'Content-Type: application/json' \
  -d '{"topic": "why the sky is blue"}'

curl -N -X POST "localhost:18282/langchain/streaming?model=gemma4" \
  -H 'Content-Type: application/json' \
  -d '{"topic": "why the sky is blue"}'
```

The `-N` flag disables curl's output buffering so chunks print as they
arrive instead of all at once at the end.

## Gotchas

- SSE data lines are one `data: <chunk>` per streamed piece, ending in a
  blank line; the stream ends with `event: done\ndata: [DONE]\n\n` so a
  client knows when to stop listening.
- `?model=gemma4` streams real content but interleaves many empty-string
  chunks between real tokens (verified: filter out blank `data: ` lines
  and the actual words/emoji are all there). This is how
  `ChatOllama.astream()` tokenizes that model's output, not a bug in
  `stream_answer`.
