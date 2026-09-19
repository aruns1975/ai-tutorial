# RAG — Redis Backend

## What it is

`langchain_redis.RedisVectorStore`, backed by a local Redis instance with
search capability (`redis/redis-stack-server` — plain `redis:alpine` does
**not** include the Search module this needs). Defined as the `redis`
service in the root `docker-compose.yml`.

## Infra prerequisites

```bash
scripts/start_infra.sh   # or: docker compose up -d redis
```

Connection is configured via `REDIS_URL` in `.env` (default
`redis://localhost:6379`).

## Code

```python
def _build_redis_store() -> RedisVectorStore:
    config = RedisConfig(
        index_name=_INDEX_NAME,
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        indexing_algorithm="HNSW",
        embedding_dimensions=_get_embedding_dim(),
        from_existing=False,
    )
    return RedisVectorStore(embeddings=qwen3_embedding_model, config=config)
```

`indexing_algorithm="HNSW"` is set for consistency with the Postgres
backend's indexing approach (see that page for the HNSW rationale).

Ingestion for Redis calls `store.add_texts(..., keys=[doc.id for doc in documents])`
directly rather than `store.add_documents(...)` — `RedisVectorStore.add_texts`
names its id parameter `keys`, not `ids`, so the generic `add_documents`
path (which passes `ids=`) would silently fail to deduplicate. Passing
`keys=` explicitly makes re-ingestion an upsert-by-key instead of creating
new hash entries every time.

## How to call it

```bash
curl -s -X POST "localhost:18282/langchain/rag/ingest?backend=redis"

curl -s -X POST "localhost:18282/langchain/rag/query?backend=redis" \
  -H 'Content-Type: application/json' -d '{"question": "What is RAG used for?"}'
```

`query` also accepts an optional `model` **query parameter**
(`?model=...`): `"llama3.2"` (default) or `"gemma4"` — see
`docs/langchain/07-rag/00-overview.md`'s "Choosing a backend and model"
section.

## Verify the index directly

```bash
docker exec -it ai_tutorial_redis redis-cli FT._LIST         # expect "ai_tutorial_rag"
docker exec -it ai_tutorial_redis redis-cli FT.INFO ai_tutorial_rag
```

## Gotchas

- Data persists in the `redis_data` Docker volume across app restarts (and
  across `docker compose restart`), but is wiped by `docker compose down -v`.
