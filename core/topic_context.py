"""
core/topic_context.py

Fetches a brief context summary for any topic/product so personas
can form informed opinions without changing their personalities.

- PlayStation 5: uses the static PS5_CONTEXT (no network call)
- Everything else: DuckDuckGo search → snippet compilation
  Falls back to DuckDuckGo Instant Answer API, then graceful empty.
"""

import requests
from context.ps5_context import PS5_CONTEXT

DEFAULT_TOPIC = "PlayStation 5"
_PS5_ALIASES = {"playstation 5", "ps5", "playstation5", "playstation"}


def is_ps5(topic: str) -> bool:
    return topic.strip().lower() in _PS5_ALIASES


def fetch_topic_context(topic: str) -> str:
    """
    Return a context block for the given topic.
    PS5 → static context. Anything else → live web search.
    """
    if is_ps5(topic):
        return PS5_CONTEXT

    print(f"[Fetching context for '{topic}'...]")
    context = _ddg_search(topic) or _ddg_instant(topic)
    if context:
        return context

    return (
        f"TOPIC: {topic}\n\n"
        f"[No additional context found. Draw on your general knowledge about {topic}.]"
    )


def _ddg_search(topic: str) -> str:
    """Use duckduckgo-search to get real web snippets."""
    try:
        from duckduckgo_search import DDGS
        snippets = []
        with DDGS() as ddgs:
            for r in ddgs.text(f"{topic} overview", max_results=5, timelimit="y"):
                body = r.get("body", "")
                if body:
                    snippets.append(f"- {r['title']}: {body[:250]}")
        if snippets:
            return f"TOPIC: {topic}\n\n" + "\n".join(snippets)
    except Exception:
        pass
    return ""


def _ddg_instant(topic: str) -> str:
    """Fallback: DuckDuckGo Instant Answer API (no key, Wikipedia-style)."""
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": topic, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=6,
        )
        data = r.json()
        abstract = data.get("AbstractText") or data.get("Abstract", "")
        if abstract:
            return f"TOPIC: {topic}\n\n{abstract}"
    except Exception:
        pass
    return ""
