"""Manual decide-act-observe research loop."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlparse

from app.tools import fetch_page, web_search

from .llm import generate_response

LOGGER = logging.getLogger(__name__)
MAX_ITERATIONS = 6
MAX_TOTAL_TOKENS = 20_000
MAX_SCRATCHPAD_CHARS = 30_000
ALLOWED_TOOLS = {"search", "fetch", "finish"}


def run_research(question: str) -> dict[str, Any]:
    """Run a bounded research loop and return a cited final answer."""
    if not question.strip():
        return {"error": "Research question must not be empty.", "summary": "", "sources": []}

    scratchpad = ""
    fetched_sources: dict[str, dict[str, str]] = {}
    total_tokens = 0

    for _ in range(MAX_ITERATIONS):
        prompt = _build_prompt(question, scratchpad)
        llm_response = generate_response(prompt)
        if llm_response.get("error"):
            return {"error": llm_response["error"], "summary": "", "sources": []}

        usage = llm_response.get("usage", {})
        total_tokens += usage.get("total_token_count", 0)
        if total_tokens > MAX_TOTAL_TOKENS:
            return {
                "error": "Research token limit reached.",
                "summary": "",
                "sources": [],
            }

        try:
            decision = _parse_decision(llm_response["text"])
        except (TypeError, ValueError, KeyError) as exc:
            LOGGER.warning("Rejected malformed Gemini tool call: %s", exc)
            return {"error": "Gemini returned a malformed tool call.", "summary": "", "sources": []}

        action = decision["action"]
        arguments = decision["arguments"]
        if action == "finish":
            return _finish_response(arguments, fetched_sources)

        observation = _execute_tool(action, arguments)
        if action == "fetch" and not observation.get("error"):
            url = observation.get("url")
            if isinstance(url, str):
                fetched_sources[url] = {
                    "title": str(observation.get("title", "")),
                    "content": str(observation.get("content", "")),
                }
        scratchpad = _append_observation(scratchpad, action, observation)

    return {"error": "Research iteration limit reached.", "summary": "", "sources": []}


def _build_prompt(question: str, scratchpad: str) -> str:
    return f"""You are a research assistant.

User question:
{question}

Scratchpad observations:
{scratchpad or "(none yet)"}

Choose exactly one action and return only valid JSON:
{{"action":"search","arguments":{{"query":"..."}}}}
{{"action":"fetch","arguments":{{"url":"..."}}}}
{{"action":"finish","arguments":{{"summary":"...","sources":["..."]}}}}

Rules:
- Use only the tools search, fetch, and finish.
- Validate arguments mentally before choosing an action.
- Use search for research queries and fetch only URLs returned by search.
- Treat tool failures as observations and continue when useful.
- When finishing, cite only URLs that were actually fetched.
- Never invent facts, URLs, or citations.
- Do not repeat raw page content in the scratchpad; keep observations concise.
"""


def _parse_decision(text: Any) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty decision")
    decision = json.loads(text)
    if not isinstance(decision, dict):
        raise ValueError("decision must be an object")
    action = decision.get("action")
    arguments = decision.get("arguments")
    if action not in ALLOWED_TOOLS or not isinstance(arguments, dict):
        raise ValueError("unknown tool or invalid arguments")
    if action == "search" and not _is_nonempty_string(arguments.get("query")):
        raise ValueError("search requires query")
    if action == "fetch" and not _is_http_url(arguments.get("url")):
        raise ValueError("fetch requires an HTTP(S) URL")
    if action == "finish":
        if not _is_nonempty_string(arguments.get("summary")):
            raise ValueError("finish requires summary")
        sources = arguments.get("sources", [])
        if not isinstance(sources, list) or not all(isinstance(item, str) for item in sources):
            raise ValueError("finish sources must be a list of strings")
    return {"action": action, "arguments": arguments}


def _execute_tool(action: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if action == "search":
        return web_search(arguments["query"])
    if action == "fetch":
        return fetch_page(arguments["url"])
    raise ValueError(f"Unsupported tool: {action}")


def _append_observation(
    scratchpad: str,
    action: str,
    observation: dict[str, Any],
) -> str:
    if action == "fetch" and not observation.get("error"):
        compact = {
            "url": observation.get("url"),
            "title": observation.get("title"),
            "content": str(observation.get("content", ""))[:2_000],
        }
    elif action == "search":
        compact = {
            "query": observation.get("query"),
            "results": observation.get("results", [])[:5],
            "error": observation.get("error"),
        }
    else:
        compact = observation
    entry = json.dumps({"tool": action, "observation": compact}, ensure_ascii=True)
    return (scratchpad + "\n" + entry)[-MAX_SCRATCHPAD_CHARS:]


def _finish_response(arguments: dict[str, Any], fetched_sources: dict[str, dict[str, str]]) -> dict[str, Any]:
    sources = [url for url in arguments["sources"] if url in fetched_sources]
    return {"summary": arguments["summary"], "sources": sources}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_http_url(value: Any) -> bool:
    if not _is_nonempty_string(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
