# RAG (Retrieval-Augmented Generation) — Overview

## Concept

Retrieval-augmented generation gives a model access to information it
wasn't trained on by searching a document collection for relevant passages
and inserting them into the prompt before asking a question. The pipeline
has four steps:

1. **Chunk** — split documents into small, overlapping pieces.
2. **Embed** — convert each chunk into a numerical vector.
3. **Store & search** — put the vectors in a vector store, and at query
   time find the chunks most similar to the question.
4. **Answer** — stuff the retrieved chunks into a prompt and ask the model.

This project demonstrates the *same* pipeline against three interchangeable
vector store backends, so you can compare them directly:

| Backend | Page | Infra |
|---|---|---|
| In-memory | [01-in-memory-backend.md](01-in-memory-backend.md) | None |
| Redis | [02-redis-backend.md](02-redis-backend.md) | `docker compose up -d redis` |
| Postgres (pgvector) | [03-postgres-backend.md](03-postgres-backend.md) | `docker compose up -d postgres` |

## Code walkthrough

See `langchain_demo/rag_demo.py`. All three backends share:
- `load_and_split_corpus()` — reads `langchain_demo/rag_corpus.md` (a short,
  self-contained sample document — no external files needed to try this)
  and splits it with `RecursiveCharacterTextSplitter`.
- The same embedding model: `models/embedding_models/ollama_models.py`'s
  `qwen3_embedding_model` (`OllamaEmbeddings`, pinned to the
  `qwen3-embedding:0.6b` tag — see the Postgres page for why).
- `_get_embedding_dim()` — probes the embedding model once and caches the
  output vector length, rather than hardcoding it, since it depends on
  which embedding model/tag is configured.
- Stable, content-derived chunk ids (`uuid.uuid5(uuid.NAMESPACE_URL, chunk)`)
  so re-ingesting the same corpus **upserts** existing chunks in persistent
  backends (redis/postgres) instead of duplicating them across app restarts.

`ingest(backend, force)` and `query(question, backend, k, model)` are the
two public entry points, both selecting a backend via the `VectorBackend`
enum (`memory` / `redis` / `postgres`). `query`'s `model` only chooses the
answer-generation model (step 4) — the embedding model used for retrieval
(steps 2–3) stays fixed regardless of `model`, so results across models
stay comparable for the same backend.

## Choosing a backend and model

Both endpoints accept `backend` as a **query parameter**
(`?backend=memory|redis|postgres`) — never a body field, same convention
as `memory_backend` elsewhere in this project. `POST /langchain/rag/ingest`
additionally accepts `force` (query param, boolean) and has no body at
all. `POST /langchain/rag/query` accepts `model` (query param,
`"llama3.2"` default or `"gemma4"`) alongside `backend`; `question` and
`k` are body fields since they're request *content*, not mode selectors.
`ingest` has no `model` param — ingestion only uses the (fixed) embedding
model, never a chat model.

## How to call it

```bash
curl -s -X POST "localhost:18282/langchain/rag/ingest?backend=memory"

curl -s -X POST "localhost:18282/langchain/rag/query?backend=memory" \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is RAG used for?"}'

# same question/backend, answered by gemma4 instead
curl -s -X POST "localhost:18282/langchain/rag/query?backend=memory&model=gemma4" \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is RAG used for?"}'
```

`backend` defaults to `RAG_DEFAULT_BACKEND` from `.env` (`memory` out of the
box) if omitted. `query` calls `ingest` automatically if the backend hasn't
been ingested yet in the current process, so you don't have to call both
endpoints yourself — though calling `ingest` explicitly first is useful to
see the chunk count.

## Gotchas

- No silent truncation: the sample corpus is deliberately small (a handful
  of paragraphs), so all three backends return meaningfully similar answers
  — this demo is about comparing *backends*, not testing retrieval quality
  at scale.
