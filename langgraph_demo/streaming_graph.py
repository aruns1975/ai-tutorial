"""
Concept: Streaming graph execution.

Contrast with langchain_demo/streaming_demo.py: that streams individual
*tokens* from one model call. A graph's `.astream(stream_mode="updates")`
streams one event *per node* as it finishes — you watch the graph's
control flow execute step by step, not the text of any single response
appear character by character. Reuses stategraph_basics.py's exact
fact -> joke graph so the two streaming styles can be compared on
identical underlying work.
"""

from collections.abc import AsyncIterator

from langgraph_demo.stategraph_basics import get_fact_joke_graph
from models.chat_models.ollama_models import SupportedModel


async def stream_stategraph_demo(topic: str, model: SupportedModel = SupportedModel.llama3_2) -> AsyncIterator[dict]:
    """
    Async-yield one {"node": str, "output": dict} event per node as the
    fact -> joke graph executes, instead of returning only the final state.
    """
    graph = get_fact_joke_graph(model)
    async for update in graph.astream({"topic": topic, "fact": "", "joke": ""}, stream_mode="updates"):
        for node_name, output in update.items():
            yield {"node": node_name, "output": output}
