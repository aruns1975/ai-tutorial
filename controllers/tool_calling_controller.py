from fastapi import APIRouter
from pydantic import BaseModel

from langchain_demo.tool_calling import run_tool_calling_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langchain/tool-calling", tags=["langchain-tool-calling"])


class MessageRequest(BaseModel):
    message: str


@router.post("")
def tool_calling(payload: MessageRequest, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """Calls `langchain_demo.tool_calling.run_tool_calling_demo`."""
    return run_tool_calling_demo(payload.message, model)
