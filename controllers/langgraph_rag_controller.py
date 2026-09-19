from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langgraph_demo.rag.graph import run_rag_demo
from langgraph_demo.rag.history_stores import HistoryBackend
from langgraph_demo.rag.vector_stores import VectorBackend
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langgraph/rag", tags=["langgraph-rag"])


class QuestionRequest(BaseModel):
    question: str


@router.post("/{session_id}")
async def rag_turn(
    session_id: str,
    payload: QuestionRequest,
    model: SupportedModel = SupportedModel.llama3_2,
    history_backend: HistoryBackend = HistoryBackend.memory,
    vector_backend: VectorBackend = VectorBackend.memory,
    rewrite_eval: bool = False,
    rerank: bool = False,
    generation_eval: bool = False,
    top_k: int = 4,
    top_n: int = 3,
) -> dict:
    """
    Calls `langgraph_demo.rag.graph.run_rag_demo`.

    `rewrite_eval`, `rerank`, and `generation_eval` are independent flags,
    each defaulting to False — enabling one has no effect on the others.
    Enabling any of them, or switching `history_backend`/`vector_backend`
    to `redis`/`postgres`, requires the matching infra/API key to be
    configured (see docs/langgraph/08-rag.md).
    """
    try:
        return await run_rag_demo(
            session_id,
            payload.question,
            model.value,
            history_backend.value,
            vector_backend.value,
            rewrite_eval,
            rerank,
            generation_eval,
            top_k,
            top_n,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
