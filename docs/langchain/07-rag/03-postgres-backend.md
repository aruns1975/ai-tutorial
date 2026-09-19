# RAG — Postgres (pgvector) Backend

## What it is

`langchain_postgres.PGVectorStore`, backed by a local Postgres instance with
the `pgvector` extension (`pgvector/pgvector:pg16` — ships the extension
pre-built, unlike plain `postgres:16`). Defined as the `postgres` service in
the root `docker-compose.yml`.

## Infra prerequisites

```bash
scripts/start_infra.sh   # prompts for Postgres creds the first time, then docker compose up -d
```

Connection is configured via `POSTGRES_HOST`/`POSTGRES_PORT`/`POSTGRES_DB`/
`POSTGRES_ROOT_USER`/`POSTGRES_APP_USER` — all plain, committed values in
`.env`, since none of them are sensitive. Only the two passwords are
indirected to your shell environment (see `scripts/lib/env.sh` for how
they're resolved/prompted):

- `POSTGRES_ROOT_USER` (plain) / `POSTGRES_ROOT_PASSWORD` (indirected) —
  the Postgres superuser, used **only** to bootstrap the container.
- `POSTGRES_APP_USER` (plain) / `POSTGRES_APP_PASSWORD` (indirected) — a
  least-privilege role created by `docker/postgres/init/002-create-app-user.sh`,
  which the application actually connects with
  (`langchain_demo/rag_demo.py`'s `_get_pg_engine()` never touches the root
  credentials).

The `vector` extension is enabled by
`docker/postgres/init/001-enable-pgvector.sql`; the app user is created by
`docker/postgres/init/002-create-app-user.sh`. Both run automatically on
first container start against a fresh volume (they will **not** re-run on
an existing volume — use `docker compose down -v` if you ever need to force
them to re-run).

## Why the embedding model is pinned to `qwen3-embedding:0.6b`

pgvector's HNSW (and IVFFlat) index has a hard **2000-dimension** limit for
the `vector` type. The larger `qwen3-embedding:4b` tag produces 2560-dim
embeddings — comfortably over that limit, and `CREATE INDEX ... USING hnsw`
fails outright against it (`ProgramLimitExceeded: column cannot have more
than 2000 dimensions for hnsw index`). The `0.6b` tag produces 1024-dim
embeddings, which indexes cleanly. See
`models/embedding_models/ollama_models.py` for the pinned model and this
comment.

All three RAG backends use the same embedding model, so this pin applies
uniformly — not just to the Postgres backend.

## Why HNSW over IVFFlat

```python
await store.aapply_vector_index(HNSWIndex(name=f"{_PG_TABLE}_hnsw_idx"))
```

HNSW was chosen over IVFFlat for two reasons specific to this tutorial's
usage pattern:
- IVFFlat's `lists` parameter needs to be tuned against the row count —
  awkward when the table starts empty and grows one `/langchain/rag/ingest`
  call at a time, rather than being bulk-loaded up front.
- HNSW degrades more gracefully under incremental, single-batch inserts;
  IVFFlat is best built *after* bulk-loading representative data.

At this tutorial's scale (one small markdown file, ~10 chunks) neither
choice affects query latency — the choice here is about not fighting the
index while inserting, not about performance at scale.

## Schema ownership

The `ai_tutorial_rag_chunks` table's schema (id/content/embedding/metadata
columns) is created entirely by `langchain-postgres`'s
`PGEngine.ainit_vectorstore_table(...)` — the init SQL script only enables
the `vector` extension, deliberately not the table itself, so there's a
single source of truth for the schema.

```python
try:
    await engine.ainit_vectorstore_table(table_name=_PG_TABLE, vector_size=_get_embedding_dim())
except Exception as exc:
    if "already exists" not in str(exc).lower():
        raise
```

Both `ainit_vectorstore_table` and `aapply_vector_index` raise if the table
or index already exists (e.g. on a second app start against an
already-provisioned database) — the demo catches and ignores that specific
case so repeated startups are idempotent.

## Ingestion (upsert, not duplicate)

```python
await store.aadd_documents(documents, ids=[doc.id for doc in documents])
```

`PGVectorStore.aadd_documents` needs `ids` passed explicitly (unlike
`InMemoryVectorStore`, it doesn't auto-read `Document.id`) — passing the
corpus's stable, content-derived ids makes re-ingestion an upsert
(`ON CONFLICT ... DO UPDATE`) instead of inserting duplicate rows.

## How to call it

```bash
curl -s -X POST "localhost:18282/langchain/rag/ingest?backend=postgres"

curl -s -X POST "localhost:18282/langchain/rag/query?backend=postgres" \
  -H 'Content-Type: application/json' -d '{"question": "What is RAG used for?"}'
```

`query` also accepts an optional `model` **query parameter**
(`?model=...`): `"llama3.2"` (default) or `"gemma4"` — see
`docs/langchain/07-rag/00-overview.md`'s "Choosing a backend and model"
section.

## Verify the extension/index/roles directly

(Use the root user, `ai_tutorial_root`, for admin queries — it's the one
with `\du`/schema-wide visibility.)

```bash
docker exec -it ai_tutorial_postgres psql -U ai_tutorial_root -d ai_tutorial_rag -c '\dx'
# expect the `vector` extension listed

docker exec -it ai_tutorial_postgres psql -U ai_tutorial_root -d ai_tutorial_rag -c '\d ai_tutorial_rag_chunks'
# expect an hnsw index on the embedding column

docker exec -it ai_tutorial_postgres psql -U ai_tutorial_root -d ai_tutorial_rag -c '\du'
# expect both ai_tutorial_root (superuser) and ai_tutorial_app (not)

docker exec -it ai_tutorial_postgres psql -U ai_tutorial_root -d ai_tutorial_rag -c '\dt'
# expect ai_tutorial_rag_chunks owned by ai_tutorial_app, not root
```

## Gotchas

- Data persists in the `postgres_data` Docker volume across app restarts,
  wiped by `docker compose down -v`.
- If you ever swap in a different embedding model/tag with a different
  output dimension, you must drop and recreate the table (the `vector_size`
  is fixed at table-creation time) — connect as the app user and
  `DROP TABLE ai_tutorial_rag_chunks;`.
- Only the two passwords (`POSTGRES_ROOT_PASSWORD`/`POSTGRES_APP_PASSWORD`)
  are indirected to variables in your shell environment (e.g.
  `RAG_DEMO_PG_ROOT_PASSWORD`) and resolved/prompted-for by
  `scripts/lib/env.sh` — the usernames (`ai_tutorial_root`/`ai_tutorial_app`)
  are plain, committed values, since a username isn't sensitive. Password
  answers are cached in a gitignored `.env.local`, which is a local-dev
  convenience only — it's not where the list of required variables lives
  (that's `.env`, committed) and it's not something a real deployment
  reads. See the project root `README.md`'s "Secrets and `.env`" section.
