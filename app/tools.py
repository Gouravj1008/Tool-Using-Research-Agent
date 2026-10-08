"""External tools used by the research agent."""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlparse

import httpx
import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
DEFAULT_TIMEOUT_SECONDS = 10
MAX_PAGE_CONTENT_LENGTH = 50_000


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


def fetch_page(url: str) -> dict[str, str]:
    """Fetch a webpage and return its title and readable text content."""
    response: dict[str, str] = {"url": url, "title": "", "content": ""}

    if not _is_valid_http_url(url):
        response["error"] = "URL must be a valid HTTP or HTTPS URL."
        LOGGER.warning("Page fetch skipped because the URL is invalid: %r.", url)
        return response

    try:
        page_response = httpx.get(
            url,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        page_response.raise_for_status()
        title, content = _parse_page(page_response.text)
        if not content:
            response["error"] = "Page did not contain readable content."
            LOGGER.info("Page contained no readable content: %s", url)
            return response
        response["title"] = title
        response["content"] = content[:MAX_PAGE_CONTENT_LENGTH]
    except httpx.TimeoutException:
        response["error"] = "Page request timed out."
        LOGGER.exception("Page request timed out for URL %r.", url)
    except httpx.HTTPStatusError:
        response["error"] = "Page returned an HTTP error."
        LOGGER.exception("Page returned an HTTP error for URL %r.", url)
    except httpx.RequestError:
        response["error"] = "Page request failed."
        LOGGER.exception("Page request failed for URL %r.", url)
    except (TypeError, ValueError):
        response["error"] = "Page could not be parsed."
        LOGGER.exception("Page parsing failed for URL %r.", url)

    return response


def _is_valid_http_url(url: str) -> bool:
    """Return whether a URL has an HTTP(S) scheme and a host."""
    if not isinstance(url, str):
        return False
    parsed_url = urlparse(url.strip())
    return parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)


def _parse_page(html: str) -> tuple[str, str]:
    """Extract the page title and readable body text from HTML."""
    if not isinstance(html, str):
        raise TypeError("Page response must contain text.")
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "template"]):
        element.decompose()
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if soup.title:
        soup.title.decompose()
    content = " ".join(soup.get_text(" ", strip=True).split())
    return title, content


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
