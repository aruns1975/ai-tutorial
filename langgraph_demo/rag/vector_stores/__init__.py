"""
Customizable vector-store backend for the LangGraph RAG concept.

Unlike history_stores/ (which gets its own per-backend files, since
memory-backed history is cheap enough to write fresh), the vector store
side is reused wholesale from langchain_demo.rag_demo: the embedding-
dimension probing, HNSW indexing, and per-backend upsert quirks
(langchain_redis's add_texts(keys=...) vs. langchain_postgres's
aadd_documents(ids=...) vs. InMemoryVectorStore's auto Document.id) were
already found and fixed getting langchain_demo/rag_demo.py right (see
its docstrings) — re-deriving that here would just reintroduce the same
bugs, not simplify anything.

sub_graphs/retriever.py imports VectorBackend and retrieve_documents
from this module rather than reaching into langchain_demo.rag_demo
directly, so a future swap of the underlying implementation only
touches this one file.
"""

from langchain_demo.rag_demo import VectorBackend, ingest, retrieve_documents

__all__ = ["VectorBackend", "ingest", "retrieve_documents"]
