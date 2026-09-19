"""
Concept: Streaming.

Streams a chain's output token-by-token as it's generated, instead of
waiting for the full response. See controllers/streaming_controller.py
for how this is exposed as a FastAPI Server-Sent Events endpoint.
"""

from collections.abc import AsyncIterator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from models.chat_models.ollama_models import SupportedModel, get_chat_model

_prompt = ChatPromptTemplate.from_messages(
    [("human", "Write a short, engaging explanation of: {topic}")]
)


async def stream_answer(topic: str, model: SupportedModel = SupportedModel.llama3_2) -> AsyncIterator[str]:
    """Async-yield text chunks as they stream from the model."""
    llm = get_chat_model(model)
    chain = _prompt | llm | StrOutputParser()
    async for chunk in chain.astream({"topic": topic}):
        yield chunk
