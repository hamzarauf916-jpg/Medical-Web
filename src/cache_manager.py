"""
cache_manager.py
-----------------
Demonstrates and toggles between LangChain's two built-in LLM caches:

- InMemoryCache: lives only in RAM, fastest, wiped on app restart.
  Best for speeding up repeated calls within a single running session.

- SQLiteCache: persisted to a .db file on disk, slightly slower than
  memory but survives restarts, and is shareable across sessions/runs.

Once a cache is registered with set_llm_cache(), LangChain checks it
automatically before every LLM call using the (prompt, model, params)
as the cache key — identical requests are served instantly from cache
instead of hitting the API again.
"""

import os
from langchain_community.cache import InMemoryCache, SQLiteCache
from langchain_core.globals import set_llm_cache

from src.config import SQLITE_CACHE_PATH

CACHE_NONE = "None (no caching)"
CACHE_MEMORY = "In-Memory Cache"
CACHE_SQLITE = "SQLite Cache"

CACHE_OPTIONS = [CACHE_NONE, CACHE_MEMORY, CACHE_SQLITE]


def apply_cache(choice: str) -> str:
    """
    Registers the chosen cache backend globally for LangChain.
    Returns a short human-readable status string for display in the UI.
    """
    if choice == CACHE_MEMORY:
        set_llm_cache(InMemoryCache())
        return "In-memory cache active — fastest, cleared when the app restarts."

    if choice == CACHE_SQLITE:
        os.makedirs(os.path.dirname(SQLITE_CACHE_PATH) or ".", exist_ok=True)
        set_llm_cache(SQLiteCache(database_path=SQLITE_CACHE_PATH))
        return f"SQLite cache active at `{SQLITE_CACHE_PATH}` — persists across restarts."

    # CACHE_NONE
    set_llm_cache(None)
    return "Caching disabled — every submission calls the API fresh."
