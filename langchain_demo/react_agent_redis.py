"""
Redis-backed checkpointer for the ReAct agent's LangGraph persistence.

LangGraph's own answer to "give this a memory" is a checkpointer attached
directly to the compiled graph — no RunnableWithMessageHistory wiring
needed (contrast with memory_conversation.py's approach for the
non-agent concepts). Uses the same local Redis instance the RAG and
Memory concepts use, under its own key/index namespace.
"""

import os

from langgraph.checkpoint.redis import RedisSaver

_CHECKPOINT_PREFIX = "ai_tutorial_agent_checkpoint"


def build_checkpointer() -> RedisSaver:
    """
    Build and initialize a Redis-backed checkpointer. Called once per
    process (see react_agent.py's agent cache) — RedisSaver itself is a
    thread-safe handle to Redis, not something that needs per-call
    construction the way memory_conversation_redis.py's history objects
    did.
    """
    saver = RedisSaver(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        checkpoint_prefix=_CHECKPOINT_PREFIX,
    )
    saver.setup()
    return saver
