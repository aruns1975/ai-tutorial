from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langchain_demo.memory_conversation import (
    MemoryBackend,
    clear_conversation,
    get_conversation_history,
    run_conversation_turn,
)
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langchain/memory", tags=["langchain-memory"])


class MessageRequest(BaseModel):
    message: str


@router.post("/{session_id}")
def memory_turn(
    session_id: str,
    payload: MessageRequest,
    model: SupportedModel = SupportedModel.llama3_2,
    memory_backend: MemoryBackend = MemoryBackend.memory,
) -> dict:
    """Calls `langchain_demo.memory_conversation.run_conversation_turn`."""
    return run_conversation_turn(session_id, payload.message, model, memory_backend)


@router.get("/{session_id}")
def memory_history(session_id: str, memory_backend: MemoryBackend = MemoryBackend.memory) -> dict:
    """Calls `langchain_demo.memory_conversation.get_conversation_history`."""
    messages = get_conversation_history(session_id, memory_backend)
    if not messages:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "backend": memory_backend.value, "messages": messages}


@router.delete("/{session_id}")
def memory_clear(session_id: str, memory_backend: MemoryBackend = MemoryBackend.memory) -> dict:
    """Calls `langchain_demo.memory_conversation.clear_conversation`."""
    cleared = clear_conversation(session_id, memory_backend)
    return {"session_id": session_id, "backend": memory_backend.value, "cleared": cleared}
