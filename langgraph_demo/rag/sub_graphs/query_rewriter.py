"""
Sub-graph 1 of the LangGraph RAG concept: query rewriting.

Takes the current question plus prior conversation turns. If there IS
history, asks the LLM to rewrite the question into a standalone query
that doesn't depend on references from earlier turns — e.g. given a
prior "What is the capital of India?" / "Delhi" exchange, "Where is it
located?" gets rewritten to "Where is Delhi located?". Without this,
the vector store would be searched for "it", which matches nothing
useful. If there's no history, this is a pass-through:
rewritten_query == question.

Whether history is present is decided by a plain Python conditional
edge on state["history"], not an LLM judgment call — cheaper, and
deterministic (mirrors the reference project's query_reformatter.py).

Optionally (rewrite_eval=True) asks Cohere to judge the rewrite's
quality — but only when a rewrite actually happened; evaluating a
pass-through against itself is meaningless, so the eval node is skipped
whenever was_rewritten is False regardless of the flag.
"""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from langgraph_demo.rag import cohere_client
from langgraph_demo.rag.state import QueryRewriterState
from models.chat_models.ollama_models import SupportedModel, get_chat_model

_REWRITE_PROMPT = (
    "Conversation so far:\n{history}\n\n"
    'The user\'s latest question is: "{question}"\n\n'
    "Rewrite the latest question as a standalone question that makes sense "
    "without the conversation above — resolve any pronouns or implicit "
    'references (e.g. "it", "that", "there") using the conversation. If the '
    "latest question is already standalone, return it unchanged. Respond "
    "with ONLY the rewritten question, nothing else."
)

_EVAL_PROMPT = (
    "You are judging a query-rewrite step in a RAG pipeline.\n"
    "Original question: {question}\n"
    "Rewritten (standalone) question: {rewritten_query}\n\n"
    "Does the rewrite correctly preserve the original intent while resolving "
    "references from prior conversation? Respond with ONLY a JSON object: "
    '{{"faithful": <0.0-1.0>, "reasoning": "<short reason>"}}'
)


def _format_history(history: list[dict]) -> str:
    return "\n".join(f"{turn['role']}: {turn['content']}" for turn in history)


def _route_on_history(state: QueryRewriterState) -> Literal["rewrite", "passthrough"]:
    return "rewrite" if state["history"] else "passthrough"


def _route_after_rewrite(state: QueryRewriterState) -> Literal["eval", "__end__"]:
    if state["rewrite_eval"] and state["was_rewritten"]:
        return "eval"
    return END


def _rewrite(state: QueryRewriterState) -> dict:
    llm = get_chat_model(SupportedModel(state["model"]))
    response = llm.invoke(
        _REWRITE_PROMPT.format(history=_format_history(state["history"]), question=state["question"])
    )
    return {"rewritten_query": response.content.strip(), "was_rewritten": True}


def _passthrough(state: QueryRewriterState) -> dict:
    return {"rewritten_query": state["question"], "was_rewritten": False}


def _eval_rewrite(state: QueryRewriterState) -> dict:
    result = cohere_client.judge(
        _EVAL_PROMPT.format(question=state["question"], rewritten_query=state["rewritten_query"])
    )
    return {"rewrite_eval_result": result}


def _build_graph():
    graph = StateGraph(QueryRewriterState)
    graph.add_node("rewrite", _rewrite)
    graph.add_node("passthrough", _passthrough)
    graph.add_node("eval", _eval_rewrite)
    graph.add_conditional_edges(START, _route_on_history)
    graph.add_conditional_edges("rewrite", _route_after_rewrite)
    graph.add_edge("passthrough", END)
    graph.add_edge("eval", END)
    return graph.compile()


# Compiled once at module load: unlike langgraph_demo's other concepts,
# this subgraph has no per-model cache to build — the model is read from
# QueryRewriterState["model"] at invoke time, not baked in at build time,
# since the parent graph (graph.py) picks the model per-request.
query_rewriter_graph = _build_graph()
