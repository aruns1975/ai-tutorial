"""
Web search tools for LLM function-calling.

These tools call the Google Custom Search JSON API, which requires
two credentials to be set as environment variables (loaded here from
a .env file in the project root, if present):

    GOOGLE_API_KEY  - an API key from Google Cloud Console with the
                      "Custom Search API" enabled.
    GOOGLE_CSE_ID   - the Search Engine ID of a Programmable Search
                      Engine (https://programmablesearchengine.google.com/),
                      configured to search the whole web.

Add both to the project's .env file:
    GOOGLE_API_KEY=your-api-key-here
    GOOGLE_CSE_ID=your-search-engine-id-here

If the credentials are missing, each tool raises a RuntimeError with
a clear setup message rather than failing with an opaque HTTP error.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

_SEARCH_ENDPOINT = "https://www.googleapis.com/customsearch/v1"


def _get_credentials() -> tuple[str, str]:
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        raise RuntimeError(
            "Missing GOOGLE_API_KEY and/or GOOGLE_CSE_ID. Set both in "
            "the project's .env file — see tools/search_tools.py for "
            "setup instructions."
        )
    return api_key, cse_id


def web_search(query: str, num_results: int = 5) -> list[dict]:
    """
    Search the web via Google Custom Search and return the top
    results as a list of {"title", "link", "snippet"} dicts.

    Call this tool for any request that needs current, real-world, or
    external information the model can't already know — "search the
    web for X", "look up X online", "find articles about X", or "what
    does the internet say about X".

    Few-shot examples (phrase -> tool call):
        "Search the web for the latest FastAPI release notes."
                            -> web_search("latest FastAPI release notes")
        "Look up who won the 2026 F1 championship."
                            -> web_search("2026 F1 championship winner")
        "Find me 3 articles about prompt engineering."
                            -> web_search("prompt engineering", num_results=3)
    """
    api_key, cse_id = _get_credentials()
    response = requests.get(
        _SEARCH_ENDPOINT,
        params={
            "key": api_key,
            "cx": cse_id,
            "q": query,
            "num": num_results,
        },
        timeout=10,
    )
    response.raise_for_status()
    items = response.json().get("items", [])
    return [
        {
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
        }
        for item in items
    ]


def web_search_top_result(query: str) -> dict | None:
    """
    Search the web and return only the single top result as a
    {"title", "link", "snippet"} dict (or None if nothing was found).

    Call this tool when the request wants a single best answer/link
    rather than a list — "what's the top result for X", "give me one
    good source for X", or "find the official site for X".

    Few-shot examples (phrase -> tool call):
        "What's the official Python documentation site?"
                        -> web_search_top_result("official Python documentation")
        "Give me the top result for 'FastAPI tutorial'."
                        -> web_search_top_result("FastAPI tutorial")
    """
    results = web_search(query, num_results=1)
    return results[0] if results else None


def web_search_site(query: str, site: str, num_results: int = 5) -> list[dict]:
    """
    Search the web restricted to a single site/domain and return
    results as a list of {"title", "link", "snippet"} dicts.

    Call this tool when the request names a specific site to search
    within — "search Wikipedia for X", "look on github.com for X", or
    "find X on reddit".

    Few-shot examples (phrase -> tool call):
        "Search Wikipedia for the history of the internet."
                -> web_search_site("history of the internet", "wikipedia.org")
        "Find FastAPI issues on GitHub about websockets."
                -> web_search_site("websockets", "github.com/fastapi/fastapi")
    """
    return web_search(f"site:{site} {query}", num_results=num_results)


def web_search_recent(query: str, days: int = 7, num_results: int = 5) -> list[dict]:
    """
    Search the web for results discussing a topic recently, by
    appending a "past N days" hint to the query and returning results
    as a list of {"title", "link", "snippet"} dicts.

    Call this tool when the request asks for recent/latest/breaking
    information — "what's the latest news on X", "find recent articles
    about X from the last week", or "any updates on X in the past 3
    days".

    Note: this is a best-effort hint passed into the search query
    itself (Google's Custom Search JSON API does not expose a strict
    date-range filter), so results should still be treated as
    approximate rather than a guaranteed date-filtered result set.

    Few-shot examples (phrase -> tool call):
        "What's the latest news on the FastAPI project?"
                    -> web_search_recent("FastAPI project news")
        "Any updates on the Mars rover in the past 3 days?"
                    -> web_search_recent("Mars rover updates", days=3)
    """
    return web_search(f"{query} (past {days} days)", num_results=num_results)