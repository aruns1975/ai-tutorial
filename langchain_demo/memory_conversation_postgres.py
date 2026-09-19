"""
Postgres-backed message history for the memory/conversation concept.

Uses langchain_postgres.PostgresChatMessageHistory, connecting as the
same least-privilege POSTGRES_APP_USER the RAG postgres backend uses
(see langchain_demo/rag_demo.py's _get_pg_engine()) — never the
POSTGRES_ROOT_USER superuser. The backing table (ai_tutorial_chat_history)
is separate from RAG's ai_tutorial_rag_chunks table and self-provisions
on first use via create_tables(), the same "let the library own the
schema" approach rag_demo.py uses for its table.

Session ids are hashed into a stable UUID (uuid.uuid5) before use: the
table's session_id column is typed UUID, but this concept accepts
arbitrary string session ids (e.g. "demo-session") like every other
backend does.

Tutorial-scale limitation: a single shared psycopg connection is reused
across all calls rather than a connection pool. psycopg connections
aren't safe for concurrent use from multiple threads — fine for this
demo's expected traffic, but a production version would use
psycopg_pool (already an installed transitive dependency) instead.
"""

import os
import uuid

import psycopg
from langchain_postgres import PostgresChatMessageHistory

_TABLE_NAME = "ai_tutorial_chat_history"

_connection: psycopg.Connection | None = None
_table_ready = False


def _get_connection() -> psycopg.Connection:
    global _connection
    if _connection is None:
        _connection = psycopg.connect(
            f"postgresql://{os.environ['POSTGRES_APP_USER']}:"
            f"{os.environ['POSTGRES_APP_PASSWORD']}@"
            f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
            f"{os.getenv('POSTGRES_PORT', '5432')}/"
            f"{os.getenv('POSTGRES_DB', 'ai_tutorial_rag')}"
        )
    return _connection


def get_history(session_id: str) -> PostgresChatMessageHistory:
    """
    Return the Postgres-backed BaseChatMessageHistory for a session,
    creating the backing table on first use if it doesn't exist yet.
    Compatible with RunnableWithMessageHistory's get_session_history
    signature, and with memory_conversation.py's other backends — all
    expose the same `.messages`/`.clear()` interface.
    """
    global _table_ready
    connection = _get_connection()
    if not _table_ready:
        PostgresChatMessageHistory.create_tables(connection, _TABLE_NAME)
        _table_ready = True

    stable_session_id = str(uuid.uuid5(uuid.NAMESPACE_URL, session_id))
    return PostgresChatMessageHistory(_TABLE_NAME, stable_session_id, sync_connection=connection)
