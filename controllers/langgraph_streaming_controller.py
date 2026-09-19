import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langgraph_demo.streaming_graph import stream_stategraph_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langgraph/streaming", tags=["langgraph-streaming"])


class TopicRequest(BaseModel):
    topic: str


async def _sse_events(topic: str, model: SupportedModel):
    async for event in stream_stategraph_demo(topic, model):
        yield f"data: {json.dumps(event)}\n\n"
    yield "event: done\ndata: [DONE]\n\n"


@router.post("")
async def streaming(payload: TopicRequest, model: SupportedModel = SupportedModel.llama3_2) -> StreamingResponse:
    """Calls `langgraph_demo.streaming_graph.stream_stategraph_demo`."""
    return StreamingResponse(_sse_events(payload.topic, model), media_type="text/event-stream")
