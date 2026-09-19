"""
Redis-backed message history for the memory/conversation concept.

Redis itself is the persistent store, so — unlike memory_conversation.py's
in-memory dict — there's no *data* a closure needs to protect here. But a
closure still earns its keep for a different reason: constructing
RedisChatMessageHistory re-declares its RediSearch index every time (see
the overwrite_index note below), which triggers a background reindex.
Reconstructing it on every call to get_history() means a read can race
that reindex and see a stale, partial result. create_history_cache()
caches one instance per session_id so the index is only (re)built once,
the first time that session is touched — not once per turn.
"""

import os

from langchain_redis import RedisChatMessageHistory

_KEY_PREFIX = "ai_tutorial_memory:"


def create_history_cache():
    """Return a get_history(session_id) closure backed by a private
    per-session cache of RedisChatMessageHistory instances."""
    cache: dict[str, RedisChatMessageHistory] = {}

    def get_history(session_id: str) -> RedisChatMessageHistory:
        if session_id not in cache:
            cache[session_id] = RedisChatMessageHistory(
                session_id=session_id,
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
                key_prefix=_KEY_PREFIX,
                # Works around a bug in langchain_redis 0.2.5: when the
                # search index already exists, _create_search_index()
                # tries to parse FT.INFO's "index_definition" as a list
                # (`.index("prefixes")`), but it comes back as a dict on
                # this Redis/RedisVL version, raising AttributeError.
                # overwrite_index=True skips that broken existence-check
                # code path entirely and just re-declares the schema —
                # per redisvl's SearchIndex.create(overwrite=True,
                # drop=False) semantics (the default here), this does NOT
                # delete already-stored messages. Caching the instance
                # (above) means this only runs once per session, not on
                # every call, avoiding a reindex race that otherwise
                # makes `.messages` briefly return an incomplete list.
                overwrite_index=True,
            )
        return cache[session_id]

    return get_history


get_history = create_history_cache()
