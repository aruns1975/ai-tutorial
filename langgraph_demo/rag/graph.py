"""
Parent graph for the LangGraph RAG concept: stitches together the three
independently-compiled sub-graphs (sub_graphs/query_rewriter.py,
retriever.py, generator.py) plus a history-persistence step.

    START -> query_rewriter -> retriever -> generator -> persist_turn -> END

Each subgraph has its own narrow TypedDict state (see state.py's
docstring for why), so this file's four node functions are thin
wrappers: translate the relevant slice of RagState into a subgraph's
input shape, invoke that subgraph, and merge its output back into
RagState. This is deliberately NOT done by embedding the compiled
subgraphs directly as parent nodes (which LangGraph does support when
state schemas are compatible) — here they aren't compatible, since
RagState carries fields (session_id, history_backend, ...) no single
subgraph needs, and each subgraph carries fields RagState doesn't
(e.g. QueryRewriterState.history).

The retriever subgraph's retrieve node is async (it calls
vector_stores.retrieve_documents(), async to support the Postgres
backend's async driver), so `_run_retriever` and this whole parent
graph must be invoked with `.ainvoke()`. Mixing sync node functions
(the other three) with one async node under `.ainvoke()` is fine —
LangGraph runs sync nodes inline and awaits async ones.
"""

from langgraph.graph import END, START, StateGraph

from langgraph_demo.rag.history_stores import HistoryBackend, append_turn, get_turns
from langgraph_demo.rag.state import RagState
from langgraph_demo.rag.sub_graphs.generator import generator_graph
from langgraph_demo.rag.sub_graphs.query_rewriter import query_rewriter_graph
from langgraph_demo.rag.sub_graphs.retriever import retriever_graph


def _run_query_rewriter(state: RagState) -> dict:
    history = get_turns(state["session_id"], HistoryBackend(state["history_backend"]))
    result = query_rewriter_graph.invoke(
        {
            "question": state["question"],
            "history": history,
            "model": state["model"],
            "rewrite_eval": state["rewrite_eval"],
            "rewritten_query": "",
            "was_rewritten": False,
            "rewrite_eval_result": None,
        }
    )
    return {
        "rewritten_query": result["rewritten_query"],
        "was_rewritten": result["was_rewritten"],
        "rewrite_eval_result": result["rewrite_eval_result"],
    }


async def _run_retriever(state: RagState) -> dict:
    result = await retriever_graph.ainvoke(
        {
            "query": state["rewritten_query"],
            "vector_backend": state["vector_backend"],
            "top_k": state["top_k"],
            "top_n": state["top_n"],
            "rerank": state["rerank"],
            "documents": [],
            "reranked": False,
        }
    )
    return {"documents": result["documents"], "reranked": result["reranked"]}


def _run_generator(state: RagState) -> dict:
    result = generator_graph.invoke(
        {
            "query": state["rewritten_query"],
            "documents": state["documents"],
            "model": state["model"],
            "generation_eval": state["generation_eval"],
            "answer": "",
            "generation_eval_result": None,
        }
    )
    return {"answer": result["answer"], "generation_eval_result": result["generation_eval_result"]}


def _persist_turn(state: RagState) -> dict:
    append_turn(state["session_id"], HistoryBackend(state["history_backend"]), state["question"], state["answer"])
    return {}


def build_rag_graph():
    graph = StateGraph(RagState)
    graph.add_node("query_rewriter", _run_query_rewriter)
    graph.add_node("retriever", _run_retriever)
    graph.add_node("generator", _run_generator)
    graph.add_node("persist_turn", _persist_turn)
    graph.add_edge(START, "query_rewriter")
    graph.add_edge("query_rewriter", "retriever")
    graph.add_edge("retriever", "generator")
    graph.add_edge("generator", "persist_turn")
    graph.add_edge("persist_turn", END)
    return graph.compile()


# Compiled once at module load: no per-model/per-backend caching needed
# here (unlike langgraph_demo's other concepts) since every backend
# choice is read from RagState at invoke time by the wrapper nodes
# above, not baked into the graph at build time.
rag_graph = build_rag_graph()


async def run_rag_demo(
    session_id: str,
    question: str,
    model: str = "llama3.2",
    history_backend: str = "memory",
    vector_backend: str = "memory",
    rewrite_eval: bool = False,
    rerank: bool = False,
    generation_eval: bool = False,
    top_k: int = 4,
    top_n: int = 3,
) -> dict:
    """
    Run one full turn of the query-rewriter -> retriever -> generator
    pipeline for `session_id`, persisting the turn to `history_backend`
    on completion.

    `rewrite_eval`/`rerank`/`generation_eval` are three fully independent
    flags — each defaults to False (no rewrite evaluation, no retrieval
    reranking, no generation evaluation), and any subset can be enabled
    per-request without affecting the others.

    Returns {"session_id", "question", "rewritten_query", "was_rewritten",
    "rewrite_eval_result", "documents", "reranked", "answer",
    "generation_eval_result"}.
    """
    result = await rag_graph.ainvoke(
        {
            "session_id": session_id,
            "question": question,
            "history_backend": history_backend,
            "vector_backend": vector_backend,
            "model": model,
            "rewrite_eval": rewrite_eval,
            "rerank": rerank,
            "generation_eval": generation_eval,
            "top_k": top_k,
            "top_n": top_n,
            "rewritten_query": "",
            "was_rewritten": False,
            "rewrite_eval_result": None,
            "documents": [],
            "reranked": False,
            "answer": "",
            "generation_eval_result": None,
        }
    )
    return {
        "session_id": session_id,
        "question": question,
        "rewritten_query": result["rewritten_query"],
        "was_rewritten": result["was_rewritten"],
        "rewrite_eval_result": result["rewrite_eval_result"],
        "documents": result["documents"],
        "reranked": result["reranked"],
        "answer": result["answer"],
        "generation_eval_result": result["generation_eval_result"],
    }
