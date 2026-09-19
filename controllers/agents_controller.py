from fastapi import APIRouter
from pydantic import BaseModel

from langchain_demo.react_agent import AgentMemoryBackend, run_agent_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langchain/agents", tags=["langchain-agents"])


class MessageRequest(BaseModel):
    message: str


@router.post("")
def agents(
    payload: MessageRequest,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: AgentMemoryBackend = AgentMemoryBackend.memory,
    session_id: str | None = None,
) -> dict:
    """Calls `langchain_demo.react_agent.run_agent_demo`."""
    return run_agent_demo(payload.message, model, memory_backend, session_id)
