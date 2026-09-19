# RAG — In-Memory Backend

## What it is

`langchain_core.vectorstores.InMemoryVectorStore` — a plain Python
dict-backed vector store, no external service required. It's the fastest
way to try the RAG pipeline, and the default backend
(`RAG_DEFAULT_BACKEND=memory` in `.env`).

## Code

```python
def _build_memory_store() -> InMemoryVectorStore:
    return InMemoryVectorStore(embedding=qwen3_embedding_model)
```

Ingestion just calls `store.add_documents(documents)` — the base
`VectorStore.add_documents` implementation automatically reads each
`Document.id` and upserts by it, so re-ingesting the same corpus doesn't
duplicate chunks.

## Infra prerequisites

None.

## How to call it

```bash
curl -s -X POST "localhost:18282/langchain/rag/ingest?backend=memory"

curl -s -X POST "localhost:18282/langchain/rag/query?backend=memory" \
  -H 'Content-Type: application/json' -d '{"question": "What is RAG used for?"}'
```

`query` also accepts an optional `model` **query parameter**
(`?model=...`): `"llama3.2"` (default) or `"gemma4"` — see
`docs/langchain/07-rag/00-overview.md`'s "Choosing a backend and model"
section.

## Gotchas

- Data is lost on every app restart — there's nothing to persist. Good for
  quick experiments, not for anything you need to survive a restart.
