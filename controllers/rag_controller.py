import os

from fastapi import APIRouter
from pydantic import BaseModel

from langchain_demo.rag_demo import VectorBackend, ingest, query
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langchain/rag", tags=["langchain-rag"])

_DEFAULT_BACKEND = VectorBackend(os.getenv("RAG_DEFAULT_BACKEND", "memory"))


class QueryRequest(BaseModel):
    question: str
    k: int = 4


@router.post("/ingest")
async def rag_ingest(backend: VectorBackend = _DEFAULT_BACKEND, force: bool = False) -> dict:
    """Calls `langchain_demo.rag_demo.ingest`."""
    return await ingest(backend, force)


@router.post("/query")
async def rag_query(
    payload: QueryRequest,
    backend: VectorBackend = _DEFAULT_BACKEND,
    model: SupportedModel = SupportedModel.llama3_2,
) -> dict:
    """Calls `langchain_demo.rag_demo.query`."""
    return await query(payload.question, backend, payload.k, model)
