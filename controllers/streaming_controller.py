from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain_demo.streaming_demo import stream_answer
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langchain/streaming", tags=["langchain-streaming"])


class TopicRequest(BaseModel):
    topic: str


async def _sse_events(topic: str, model: SupportedModel):
    async for chunk in stream_answer(topic, model):
        yield f"data: {chunk}\n\n"
    yield "event: done\ndata: [DONE]\n\n"


@router.post("")
async def streaming(payload: TopicRequest, model: SupportedModel = SupportedModel.llama3_2) -> StreamingResponse:
    """Calls `langchain_demo.streaming_demo.stream_answer`."""
    return StreamingResponse(_sse_events(payload.topic, model), media_type="text/event-stream")
