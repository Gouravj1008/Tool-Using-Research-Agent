"""Gemini provider adapter for the research agent."""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import errors
from google.genai import types

LOGGER = logging.getLogger(__name__)
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"


def generate_response(prompt: str) -> dict[str, Any]:
    """Generate a response through Gemini without exposing provider details."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY is not configured.", "text": ""}

    model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
    if not model:
        return {"error": "GEMINI_MODEL is not configured.", "text": ""}
    if not prompt.strip():
        return {"error": "Prompt must not be empty.", "text": ""}

    try:
        client = genai.Client(api_key=api_key)
        result = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        text = getattr(result, "text", None)
        if not isinstance(text, str) or not text.strip():
            return {"error": "Gemini returned an empty response.", "text": ""}
        usage = getattr(result, "usage_metadata", None)
        return {
            "text": text,
            "usage": _usage_to_dict(usage),
            "model": model,
        }
    except errors.APIError as exc:
        status_code = getattr(exc, "code", None)
        if status_code == 429:
            LOGGER.error("Gemini rate limit reached.")
            return {"error": "Gemini rate limit reached.", "text": ""}
        LOGGER.error("Gemini API request failed with status %s.", status_code)
        return {"error": "Gemini API request failed.", "text": ""}
    except (TypeError, ValueError):
        LOGGER.error("Gemini returned a malformed response.")
        return {"error": "Gemini returned a malformed response.", "text": ""}


def _usage_to_dict(usage: Any) -> dict[str, int]:
    """Extract token usage without logging or returning sensitive request data."""
    if usage is None:
        return {}
    result: dict[str, int] = {}
    for name in ("prompt_token_count", "candidates_token_count", "total_token_count"):
        value = getattr(usage, name, None)
        if isinstance(value, int):
            result[name] = value
    return result
