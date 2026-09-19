"""
Shared helper for fetching a chat model instance by name.

Mirrors langchain_demo/tool_utils.py's create_tool_caller pattern: build
the model_name -> instance lookup once (at import time, in
models/chat_models/ollama_models.py), then call the returned closure
wherever a concept needs to resolve a request's chosen model instead of
hardcoding one.
"""

from collections.abc import Callable

from langchain_ollama import ChatOllama


def fetch_all_models(models: list[ChatOllama]) -> Callable[[str], ChatOllama]:
    """
    Given a list of already-instantiated chat models, build a
    {model_name: instance} dict once (keyed by each model's own
    `.model` attribute, e.g. "llama3.2") and return a closure that
    looks one up by that name.

    Usage:
        get_chat_model = fetch_all_models([llama3_2_llm, gemma4_llm])
        get_chat_model("gemma4")  # -> gemma4_llm
    """
    models_by_name = {model.model: model for model in models}

    def get_model(name: str) -> ChatOllama:
        return models_by_name[name]

    return get_model
