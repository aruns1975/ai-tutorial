from fastapi import APIRouter
from pydantic import BaseModel

from langgraph_demo.stategraph_basics import run_stategraph_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langgraph/stategraph", tags=["langgraph-stategraph"])


class TopicRequest(BaseModel):
    topic: str


@router.post("")
def stategraph(payload: TopicRequest, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """Calls `langgraph_demo.stategraph_basics.run_stategraph_demo`."""
    return run_stategraph_demo(payload.topic, model)
