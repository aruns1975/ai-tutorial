"""
Concept: Retrieval-Augmented Generation (RAG).

Demonstrates the same ingest -> embed -> store -> retrieve -> answer
pipeline against THREE interchangeable vector store backends, so the
trade-offs between them are visible side by side:

- memory   -> langchain_core.vectorstores.InMemoryVectorStore
              Zero infra, lost on process restart. Good for quick
              experiments.
- redis    -> langchain_redis.RedisVectorStore, backed by a local
              Redis Stack instance (see docker-compose.yml). Fast,
              can persist to disk depending on Redis config.
- postgres -> langchain_postgres.PGVectorStore, backed by a local
              Postgres + pgvector instance (see docker-compose.yml).
              Durable, HNSW-indexed for approximate nearest-neighbor
              search at scale.

All three backends share the same chunking + embedding pipeline and
the same (now-fixed) OllamaEmbeddings model, so their answers are
directly comparable.

Sample corpus: rag_corpus.md (checked into this package) — no
external documents are required to see the demo work.
"""

import os
import uuid
from enum import Enum
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_postgres import PGEngine, PGVectorStore
from langchain_postgres.v2.indexes import HNSWIndex
from langchain_redis import RedisConfig, RedisVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from models.chat_models.ollama_models import SupportedModel, get_chat_model
from models.embedding_models.ollama_models import qwen3_embedding_model

CORPUS_PATH = Path(__file__).parent / "rag_corpus.md"

_INDEX_NAME = "ai_tutorial_rag"
_PG_TABLE = "ai_tutorial_rag_chunks"


class VectorBackend(str, Enum):
    memory = "memory"
    redis = "redis"
    postgres = "postgres"


_stores: dict[VectorBackend, object] = {}
_ingested: dict[VectorBackend, bool] = {}
_embedding_dim: int | None = None
_pg_engine: PGEngine | None = None


def _get_embedding_dim() -> int:
    """
    Probe qwen3_embedding_model once and cache the resulting vector
    length. Not hardcoded, since it depends on which qwen3-embedding
    tag (0.6b/4b/8b) is pulled locally — each has a different output
    dimension.
    """
    global _embedding_dim
    if _embedding_dim is None:
        _embedding_dim = len(qwen3_embedding_model.embed_query("dimension probe"))
    return _embedding_dim


def load_and_split_corpus(chunk_size: int = 500, chunk_overlap: int = 50) -> list[Document]:
    """
    Read CORPUS_PATH and split it into overlapping chunks. Each chunk
    gets a stable id (a UUID5 hash of its own text), so re-ingesting
    the same corpus into a persistent backend (redis/postgres) upserts
    existing chunks instead of duplicating them.
    """
    text = CORPUS_PATH.read_text()
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return [
        Document(page_content=chunk, id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk)))
        for chunk in splitter.split_text(text)
    ]


def _build_memory_store() -> InMemoryVectorStore:
    return InMemoryVectorStore(embedding=qwen3_embedding_model)


def _build_redis_store() -> RedisVectorStore:
    config = RedisConfig(
        index_name=_INDEX_NAME,
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        indexing_algorithm="HNSW",
        embedding_dimensions=_get_embedding_dim(),
        from_existing=False,
    )
    return RedisVectorStore(embeddings=qwen3_embedding_model, config=config)


def _get_pg_engine() -> PGEngine:
    """
    Connects as the least-privilege POSTGRES_APP_USER (created by
    docker/postgres/init/002-create-app-user.sh), never the
    POSTGRES_ROOT_USER superuser used only to bootstrap the container.
    """
    global _pg_engine
    if _pg_engine is None:
        url = (
            f"postgresql+psycopg://{os.environ['POSTGRES_APP_USER']}:"
            f"{os.environ['POSTGRES_APP_PASSWORD']}@"
            f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
            f"{os.getenv('POSTGRES_PORT', '5432')}/"
            f"{os.getenv('POSTGRES_DB', 'ai_tutorial_rag')}"
        )
        _pg_engine = PGEngine.from_connection_string(url=url)
    return _pg_engine


async def _build_postgres_store() -> PGVectorStore:
    engine = _get_pg_engine()

    # ainit_vectorstore_table / aapply_vector_index raise if the table or
    # index already exist (e.g. on app restart against an already-set-up
    # database) — treat "already exists" as success rather than an error.
    try:
        await engine.ainit_vectorstore_table(table_name=_PG_TABLE, vector_size=_get_embedding_dim())
    except Exception as exc:
        if "already exists" not in str(exc).lower():
            raise

    store = await PGVectorStore.create(engine=engine, embedding_service=qwen3_embedding_model, table_name=_PG_TABLE)

    try:
        await store.aapply_vector_index(HNSWIndex(name=f"{_PG_TABLE}_hnsw_idx"))
    except Exception as exc:
        if "already exists" not in str(exc).lower():
            raise

    return store


async def get_vector_store(backend: VectorBackend):
    """Return the cached store for `backend`, building it on first use."""
    if backend not in _stores:
        if backend is VectorBackend.memory:
            _stores[backend] = _build_memory_store()
        elif backend is VectorBackend.redis:
            _stores[backend] = _build_redis_store()
        else:
            _stores[backend] = await _build_postgres_store()
    return _stores[backend]


async def ingest(backend: VectorBackend = VectorBackend.memory, force: bool = False) -> dict:
    """
    Load, chunk, embed, and upsert the sample corpus into `backend`,
    unless it was already ingested (skip that check with force=True).

    Returns {"backend": str, "chunks_ingested": int}.
    """
    if _ingested.get(backend) and not force:
        return {"backend": backend.value, "chunks_ingested": 0}

    store = await get_vector_store(backend)
    documents = load_and_split_corpus()

    if backend is VectorBackend.postgres:
        # PGVectorStore.aadd_documents needs `ids` passed explicitly
        # (it doesn't auto-read Document.id) to upsert-by-id.
        await store.aadd_documents(documents, ids=[doc.id for doc in documents])
    elif backend is VectorBackend.redis:
        # RedisVectorStore's add_texts takes `keys`, not `ids` — passing
        # `ids` (as add_documents would) is silently ignored, so call
        # add_texts directly to get upsert-by-key.
        store.add_texts(
            [doc.page_content for doc in documents],
            metadatas=[doc.metadata for doc in documents],
            keys=[doc.id for doc in documents],
        )
    else:
        # InMemoryVectorStore auto-extracts Document.id and upserts by it.
        store.add_documents(documents)

    _ingested[backend] = True
    return {"backend": backend.value, "chunks_ingested": len(documents)}


_ANSWER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Answer the question using ONLY the provided context. If the context "
            "doesn't contain the answer, say so.\n\nContext:\n{context}",
        ),
        ("human", "{question}"),
    ]
)


async def retrieve_documents(question: str, backend: VectorBackend = VectorBackend.memory, k: int = 4) -> list[Document]:
    """
    Ensure `backend` is ingested and return the top-k documents most
    similar to `question`. Factored out of `query()` so the retrieval
    step alone (embedding-dimension-safe, HNSW-indexed, upsert-correct —
    several real bugs were found and fixed getting this right, see
    CLAUDE.md) can be reused elsewhere without re-deriving it —
    `langgraph_demo/rag/vector_stores/` is the other caller.
    """
    await ingest(backend)
    store = await get_vector_store(backend)

    if backend is VectorBackend.postgres:
        return await store.asimilarity_search(question, k=k)
    return store.similarity_search(question, k=k)


async def query(
    question: str,
    backend: VectorBackend = VectorBackend.memory,
    k: int = 4,
    model: SupportedModel = SupportedModel.llama3_2,
) -> dict:
    """
    Retrieve the top-k chunks for `question`, stuff them into a prompt,
    and ask the LLM. `model` only selects the answer-generation model —
    the embedding model used for retrieval stays fixed
    (qwen3_embedding_model) across all backends/models so results stay
    directly comparable.

    Returns {"backend": str, "answer": str,
             "sources": [{"content": str, "metadata": dict}, ...]}.
    """
    docs = await retrieve_documents(question, backend, k)
    context = "\n\n".join(doc.page_content for doc in docs)
    chain = _ANSWER_PROMPT | get_chat_model(model)
    answer = chain.invoke({"context": context, "question": question}).content

    return {
        "backend": backend.value,
        "model": model,
        "answer": answer,
        "sources": [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs],
    }
