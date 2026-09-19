"""
Shared Cohere client for the LangGraph RAG concept: reranking retrieved
documents (sub_graphs/retriever.py) and LLM-as-judge evaluation of both
the query rewrite (sub_graphs/query_rewriter.py) and the final generated
answer (sub_graphs/generator.py).

Needs COHERE_API_KEY set (see .env) — but only when a request actually
opts into rerank=true, rewrite_eval=true, or generation_eval=true. All
three flags default to False, in which case this module is never
touched and no Cohere API key is required at all.
"""

import json
import os

import cohere

_RERANK_MODEL = "rerank-v3.5"
_JUDGE_MODEL = "command-r-08-2024"


def _get_client() -> cohere.Client:
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing COHERE_API_KEY. Set it in the project's .env file to use "
            "rerank=true, rewrite_eval=true, or generation_eval=true — see "
            "langgraph_demo/rag/cohere_client.py."
        )
    return cohere.Client(api_key)


def rerank(query: str, documents: list[dict], top_n: int) -> list[dict]:
    """
    Re-order `documents` (each a {"content": str, ...} dict) by
    relevance to `query` using Cohere's rerank API, keeping only the
    top `top_n`.
    """
    response = _get_client().rerank(
        model=_RERANK_MODEL,
        query=query,
        documents=[doc["content"] for doc in documents],
        top_n=min(top_n, len(documents)),
    )
    return [documents[result.index] for result in response.results]


def judge(prompt: str) -> dict:
    """
    Send `prompt` to a Cohere chat model acting as an LLM judge and
    parse its response as JSON. Returns {"raw": <response text>} if the
    response isn't valid JSON, rather than raising — a judge call that
    returns unparseable output shouldn't crash the whole request.
    """
    response = _get_client().chat(model=_JUDGE_MODEL, message=prompt)
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {"raw": response.text}
