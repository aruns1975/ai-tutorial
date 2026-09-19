"""
Sub-graph 2 of the LangGraph RAG concept: retrieval.

Straightforward compared to its siblings: fetch the top-k most similar
chunks for the (possibly rewritten) query from the configured vector
store, then optionally (rerank=True) re-order the top-k down to the
top-n most relevant using Cohere's rerank API — a cross-encoder pass
that's more accurate than the embedding similarity search alone, but
too slow/expensive to run over the whole corpus, hence "narrow with
embeddings first, then re-rank the shortlist."

The retrieve node is async (vector_stores.retrieve_documents() is
async, to support the Postgres backend's async driver), so this
subgraph — and the parent graph that embeds it — must be invoked via
.ainvoke(), not .invoke().
"""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from langgraph_demo.rag import cohere_client
from langgraph_demo.rag.state import RetrieverState
from langgraph_demo.rag.vector_stores import VectorBackend, retrieve_documents


def _route_on_rerank(state: RetrieverState) -> Literal["rerank", "__end__"]:
    return "rerank" if state["rerank"] else END


async def _retrieve(state: RetrieverState) -> dict:
    docs = await retrieve_documents(state["query"], VectorBackend(state["vector_backend"]), k=state["top_k"])
    documents = [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]
    return {"documents": documents}


def _rerank(state: RetrieverState) -> dict:
    reranked = cohere_client.rerank(state["query"], state["documents"], top_n=state["top_n"])
    return {"documents": reranked, "reranked": True}


def _build_graph():
    graph = StateGraph(RetrieverState)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("rerank", _rerank)
    graph.add_edge(START, "retrieve")
    graph.add_conditional_edges("retrieve", _route_on_rerank)
    graph.add_edge("rerank", END)
    return graph.compile()


retriever_graph = _build_graph()
