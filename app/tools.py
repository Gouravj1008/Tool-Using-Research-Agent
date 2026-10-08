"""External tools used by the research agent."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
DEFAULT_TIMEOUT_SECONDS = 10


def web_search(query: str) -> dict[str, Any]:
    """Search the web and return normalized search results.

    The Brave Search API is isolated in this module so that the public tool
    interface can remain stable if the provider changes later.
    """
    normalized_query = query.strip()
    response: dict[str, Any] = {"query": normalized_query, "results": []}

    if not normalized_query:
        response["error"] = "Search query must not be empty."
        LOGGER.warning("Search skipped because the query is empty.")
        return response

    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        response["error"] = "BRAVE_SEARCH_API_KEY is not configured."
        LOGGER.error("Search failed because BRAVE_SEARCH_API_KEY is missing.")
        return response

    try:
        provider_response = _search_brave(
            normalized_query,
            api_key,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response["results"] = _normalize_results(provider_response)
    except requests.Timeout:
        response["error"] = "Search request timed out."
        LOGGER.exception("Search request timed out for query %r.", normalized_query)
    except requests.RequestException:
        response["error"] = "Search provider request failed."
        LOGGER.exception("Search provider request failed for query %r.", normalized_query)
    except (TypeError, ValueError, KeyError):
        response["error"] = "Search provider returned an invalid response."
        LOGGER.exception("Invalid search response for query %r.", normalized_query)

    if not response["results"] and "error" not in response:
        response["message"] = "No search results found."
        LOGGER.info("Search returned no results for query %r.", normalized_query)

    return response


def _search_brave(query: str, api_key: str, *, timeout: int) -> dict[str, Any]:
    """Call the Brave Search API."""
    response = requests.get(
        BRAVE_SEARCH_URL,
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        },
        params={"q": query},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Search response must be a JSON object.")
    return payload


def _normalize_results(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Convert the provider response into the tool's stable result shape."""
    web_results = payload.get("web", {}).get("results", [])
    if not isinstance(web_results, list):
        raise TypeError("Search results must be a list.")

    results: list[dict[str, str]] = []
    for item in web_results:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        url = item.get("url")
        snippet = item.get("description", "")
        if isinstance(title, str) and isinstance(url, str):
            results.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": snippet if isinstance(snippet, str) else "",
                }
            )
    return results
