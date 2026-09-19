from enum import Enum

from langchain_ollama import ChatOllama

from models.model_utils import fetch_all_models


class SupportedModel(str, Enum):
    """Chat models this project knows how to fetch by name."""

    llama3_2 = "llama3.2"
    gemma4 = "gemma4"


gemma4_llm = ChatOllama(
    model="gemma4",
    temperature=0
)

llama3_2_llm = ChatOllama(
    model="llama3.2",
    temperature=0
)

# Built once here; every concept file imports and calls this instead of
# hardcoding a specific *_llm instance, so a request's `model` field
# resolves to the right instance without an if/elif per concept.
get_chat_model = fetch_all_models([llama3_2_llm, gemma4_llm])
