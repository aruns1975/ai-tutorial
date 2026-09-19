"""
Shared checkpointer builders for the LangGraph concepts that need
persistence (persistence.py, interrupts.py).

Unlike langchain_demo's per-concept redis/postgres file pairs (each
concept there owns its own backend-selection story — memory conversation
and the ReAct agent are each independently "this concept, three
backends"), the LangGraph concepts in *this* package share ONE
persistence story: "attach any checkpointer to any graph." Splitting the
same ~15 lines of Redis/Postgres connection code across two more file
pairs here would add no new explanation, just repetition — so it lives
once, in this file, and both persistence.py and interrupts.py import it.

Note: langgraph's PostgresSaver uses fixed table names (`checkpoints`,
`checkpoint_writes`, etc. — not parameterized per caller), so this
package's Postgres-backed graphs and langchain_demo/react_agent.py's
Postgres checkpointer all share the same physical tables, distinguished
only by `thread_id`. This is normal for LangGraph (one shared checkpoint
schema per app is the intended design), not a bug.
"""

import os
from enum import Enum

import psycopg
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.redis import RedisSaver
from psycopg.rows import dict_row


class CheckpointBackend(str, Enum):
    memory = "memory"
    redis = "redis"
    postgres = "postgres"


def build_redis_checkpointer() -> RedisSaver:
    saver = RedisSaver(
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        checkpoint_prefix="ai_tutorial_langgraph_checkpoint",
    )
    saver.setup()
    return saver


def build_postgres_checkpointer() -> PostgresSaver:
    connection = psycopg.connect(
        f"postgresql://{os.environ['POSTGRES_APP_USER']}:"
        f"{os.environ['POSTGRES_APP_PASSWORD']}@"
        f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'ai_tutorial_rag')}",
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
    )
    saver = PostgresSaver(connection)
    saver.setup()
    return saver


_CHECKPOINTER_BUILDERS = {
    CheckpointBackend.memory: InMemorySaver,
    CheckpointBackend.redis: build_redis_checkpointer,
    CheckpointBackend.postgres: build_postgres_checkpointer,
}


def build_checkpointer(backend: CheckpointBackend):
    """Build a fresh checkpointer instance for the given backend."""
    return _CHECKPOINTER_BUILDERS[backend]()
