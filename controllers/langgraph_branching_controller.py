from fastapi import APIRouter
from pydantic import BaseModel

from langgraph_demo.branching import run_branching_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langgraph/branching", tags=["langgraph-branching"])


class QuestionRequest(BaseModel):
    question: str


@router.post("")
def branching(payload: QuestionRequest, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """Calls `langgraph_demo.branching.run_branching_demo`."""
    return run_branching_demo(payload.question, model)
