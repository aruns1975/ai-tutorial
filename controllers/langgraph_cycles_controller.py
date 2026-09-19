from fastapi import APIRouter
from pydantic import BaseModel

from langgraph_demo.cycles import run_cycles_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langgraph/cycles", tags=["langgraph-cycles"])


class RefineRequest(BaseModel):
    topic: str
    max_words: int = 8
    max_attempts: int = 5


@router.post("")
def cycles(payload: RefineRequest, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """Calls `langgraph_demo.cycles.run_cycles_demo`."""
    return run_cycles_demo(payload.topic, payload.max_words, payload.max_attempts, model)
