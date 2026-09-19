"""
State shapes for the LangGraph RAG pipeline.

Each subgraph gets its own narrow TypedDict — no shared "god state"
across subgraphs — mirroring the rest of this project's LangGraph
concepts (e.g. langgraph_demo/branching.py's RouterState). RagState is
the parent graph's state; the parent's wrapper node functions
(langgraph_demo/rag/graph.py) translate RagState into/out of each
subgraph's own state.
"""

from typing import TypedDict


class HistoryTurn(TypedDict):
    role: str  # "human" | "ai"
    content: str


class QueryRewriterState(TypedDict):
    question: str
    history: list[HistoryTurn]
    model: str
    rewrite_eval: bool
    rewritten_query: str
    was_rewritten: bool
    rewrite_eval_result: dict | None


class RetrievedDocument(TypedDict):
    content: str
    metadata: dict


class RetrieverState(TypedDict):
    query: str
    vector_backend: str
    top_k: int
    top_n: int
    rerank: bool
    documents: list[RetrievedDocument]
    reranked: bool


class GeneratorState(TypedDict):
    query: str
    documents: list[RetrievedDocument]
    model: str
    generation_eval: bool
    answer: str
    generation_eval_result: dict | None


class RagState(TypedDict):
    session_id: str
    question: str
    history_backend: str
    vector_backend: str
    model: str
    rewrite_eval: bool
    rerank: bool
    generation_eval: bool
    top_k: int
    top_n: int
    rewritten_query: str
    was_rewritten: bool
    rewrite_eval_result: dict | None
    documents: list[RetrievedDocument]
    reranked: bool
    answer: str
    generation_eval_result: dict | None
