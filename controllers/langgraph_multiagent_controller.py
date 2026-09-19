from fastapi import APIRouter
from pydantic import BaseModel

from langgraph_demo.multi_agent import run_multi_agent_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langgraph/multi-agent", tags=["langgraph-multi-agent"])


class RequestBody(BaseModel):
    request: str


@router.post("")
def multi_agent(payload: RequestBody, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """Calls `langgraph_demo.multi_agent.run_multi_agent_demo`."""
    return run_multi_agent_demo(payload.request, model)
