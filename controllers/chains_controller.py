from fastapi import APIRouter
from pydantic import BaseModel

from langchain_demo.lcel_chains import run_parallel_chain_demo, run_pipe_chain_demo
from models.chat_models.ollama_models import SupportedModel

router = APIRouter(prefix="/langchain/chains", tags=["langchain-chains"])


class TextRequest(BaseModel):
    text: str


class TopicRequest(BaseModel):
    topic: str


@router.post("/pipe")
def chains_pipe(payload: TextRequest, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """Calls `langchain_demo.lcel_chains.run_pipe_chain_demo`."""
    return run_pipe_chain_demo(payload.text, model)


@router.post("/parallel")
def chains_parallel(payload: TopicRequest, model: SupportedModel = SupportedModel.llama3_2) -> dict:
    """Calls `langchain_demo.lcel_chains.run_parallel_chain_demo`."""
    return run_parallel_chain_demo(payload.topic, model)
