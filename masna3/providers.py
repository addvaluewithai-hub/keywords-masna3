"""Source adapters. Unofficial suggestion endpoints require explicit opt-in."""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    pass


def _json(url: str, headers: dict[str, str] | None = None):
    request = Request(url, headers={
        "User-Agent": "KeywordsMasna3/0.1 (+https://github.com/addvaluewithai-hub/keywords-masna3)",
        "Accept": "application/json",
        **(headers or {}),
    })
    try:
        with urlopen(request, timeout=12) as response:
            return json.load(response)
    except HTTPError as exc:
        raise ProviderError(f"HTTP {exc.code}") from exc
    except (URLError, TimeoutError, ValueError) as exc:
        raise ProviderError(type(exc).__name__) from exc


def available(name: str, allow_unofficial: bool) -> tuple[bool, str]:
    if name == "brave":
        return (True, "") if os.getenv("BRAVE_API_KEY") else (False, "BRAVE_API_KEY not configured")
    if name in {"google", "duckduckgo"}:
        return ((True, "") if allow_unofficial
                else (False, "unofficial source disabled; pass --allow-unofficial explicitly"))
    return False, "unknown provider"


def suggest(name: str, query: str, language: str, country: str) -> list[str]:
    if name == "brave":
        key = os.getenv("BRAVE_API_KEY")
        if not key:
            raise ProviderError("BRAVE_API_KEY not configured")
        url = "https://api.search.brave.com/res/v1/suggest/search?" + urlencode({
            "q": query, "country": country.upper(), "count": 10,
        })
        data = _json(url, {"X-Subscription-Token": key})
        phrases = [item.get("query", "") for item in data.get("results", [])]
    elif name == "google":
        url = "https://suggestqueries.google.com/complete/search?" + urlencode({
            "client": "firefox", "q": query, "hl": language, "gl": country.lower(),
        })
        data = _json(url)
        phrases = data[1] if isinstance(data, list) and len(data) > 1 else []
    elif name == "duckduckgo":
        url = "https://duckduckgo.com/ac/?" + urlencode({"q": query, "type": "list"})
        data = _json(url)
        phrases = [item.get("phrase", "") for item in data if isinstance(item, dict)]
    else:
        raise ProviderError(f"Unknown provider: {name}")
    deduplicated = {}
    for phrase in phrases:
        if isinstance(phrase, str) and 2 <= len(phrase.strip()) <= 180:
            deduplicated.setdefault(phrase.casefold().strip(), phrase.strip())
    return list(deduplicated.values())
