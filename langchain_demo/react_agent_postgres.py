"""
Postgres-backed checkpointer for the ReAct agent's LangGraph persistence.

Connects as the same least-privilege POSTGRES_APP_USER the RAG and Memory
concepts' postgres backends use (never the POSTGRES_ROOT_USER superuser).
The connection is opened with autocommit=True, prepare_threshold=0, and
row_factory=dict_row — the exact settings PostgresSaver.from_conn_string
uses internally; PostgresSaver's own cursor/migration logic assumes an
autocommit connection and doesn't call .commit() itself.
"""

import os

import psycopg
from psycopg.rows import dict_row

from langgraph.checkpoint.postgres import PostgresSaver


def build_checkpointer() -> PostgresSaver:
    """
    Build and initialize a Postgres-backed checkpointer. Called once per
    process (see react_agent.py's agent cache).

    Tutorial-scale limitation: a single connection is held for the
    process lifetime rather than a connection pool — same trade-off as
    memory_conversation_postgres.py, acceptable for this demo's traffic.
    """
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
