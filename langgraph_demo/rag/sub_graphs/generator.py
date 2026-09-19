"""
Sub-graph 3 of the LangGraph RAG concept: generation.

The actual RAG answer: stuff the retrieved (optionally reranked)
documents into a prompt as context, ask the LLM to answer the query
using only that context. Optionally (generation_eval=True) asks Cohere
to act as an LLM judge, scoring the answer's groundedness (is it
actually supported by the retrieved context, not hallucinated),
relevance (does it address the question asked), and completeness
(does it fully answer, not just partially) — each 0.0-1.0.
"""

from typing import Literal

from langgraph.graph import END, START, StateGraph

from langgraph_demo.rag import cohere_client
from langgraph_demo.rag.state import GeneratorState
from models.chat_models.ollama_models import SupportedModel, get_chat_model

_ANSWER_PROMPT = (
    "Answer the question using ONLY the provided context. If the context "
    "doesn't contain the answer, say so.\n\n"
    "Context:\n{context}\n\n"
    "Question: {query}"
)

_EVAL_PROMPT = (
    "You are judging a RAG (retrieval-augmented generation) answer.\n"
    "Question: {query}\n"
    "Context provided to the model:\n{context}\n\n"
    "Generated answer: {answer}\n\n"
    "Score the answer 0.0-1.0 on each of:\n"
    "- groundedness: is it actually supported by the context, not hallucinated?\n"
    "- relevance: does it address the question asked?\n"
    "- completeness: does it fully answer, not just partially?\n\n"
    "Respond with ONLY a JSON object: "
    '{{"groundedness": <0.0-1.0>, "relevance": <0.0-1.0>, "completeness": <0.0-1.0>, '
    '"reasoning": "<short reason>"}}'
)


def _format_context(documents: list[dict]) -> str:
    return "\n\n".join(doc["content"] for doc in documents)


def _route_on_eval(state: GeneratorState) -> Literal["eval", "__end__"]:
    return "eval" if state["generation_eval"] else END


def _generate(state: GeneratorState) -> dict:
    llm = get_chat_model(SupportedModel(state["model"]))
    context = _format_context(state["documents"])
    response = llm.invoke(_ANSWER_PROMPT.format(context=context, query=state["query"]))
    return {"answer": response.content}


def _eval_generation(state: GeneratorState) -> dict:
    context = _format_context(state["documents"])
    result = cohere_client.judge(
        _EVAL_PROMPT.format(query=state["query"], context=context, answer=state["answer"])
    )
    return {"generation_eval_result": result}


def _build_graph():
    graph = StateGraph(GeneratorState)
    graph.add_node("generate", _generate)
    graph.add_node("eval", _eval_generation)
    graph.add_edge(START, "generate")
    graph.add_conditional_edges("generate", _route_on_eval)
    graph.add_edge("eval", END)
    return graph.compile()


generator_graph = _build_graph()
