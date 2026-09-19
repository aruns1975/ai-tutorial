from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langgraph_demo.checkpointers import CheckpointBackend
from langgraph_demo.interrupts import resume_approval_demo, start_approval_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langgraph/interrupts", tags=["langgraph-interrupts"])


class StartRequest(BaseModel):
    request: str
    session_id: str


class ResumeRequest(BaseModel):
    session_id: str
    approved: bool


@router.post("/start")
def interrupts_start(
    payload: StartRequest,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: CheckpointBackend = CheckpointBackend.memory,
) -> dict:
    """Calls `langgraph_demo.interrupts.start_approval_demo`."""
    return start_approval_demo(payload.request, payload.session_id, model, memory_backend)


@router.post("/resume")
def interrupts_resume(
    payload: ResumeRequest,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: CheckpointBackend = CheckpointBackend.memory,
) -> dict:
    """Calls `langgraph_demo.interrupts.resume_approval_demo`."""
    try:
        return resume_approval_demo(payload.session_id, payload.approved, model, memory_backend)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
