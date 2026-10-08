"""Tests for the Gemini adapter and manual research loop."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from google.genai import errors

from agent.llm import generate_response
from agent.research import run_research


class GeminiAdapterTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_returns_error_without_client(self) -> None:
        with patch("agent.llm.genai.Client") as mock_client:
            result = generate_response("Return JSON.")

        self.assertEqual(result["error"], "GEMINI_API_KEY is not configured.")
        mock_client.assert_not_called()

    @patch.dict(
        os.environ,
        {"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "test-model"},
        clear=True,
    )
    @patch("agent.llm.genai.Client")
    def test_response_is_returned_without_logging_secret(self, mock_client: Mock) -> None:
        mock_client.return_value.models.generate_content.return_value = SimpleNamespace(
            text='{"action":"finish","arguments":{"summary":"Done","sources":[]}}',
            usage_metadata=SimpleNamespace(total_token_count=10),
        )

        result = generate_response("Return JSON.")

        self.assertIn('"action":"finish"', result["text"])
        self.assertEqual(result["usage"]["total_token_count"], 10)
        mock_client.assert_called_once_with(api_key="test-key")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True)
    @patch("agent.llm.genai.Client")
    def test_rate_limit_returns_safe_error(self, mock_client: Mock) -> None:
        mock_client.return_value.models.generate_content.side_effect = errors.APIError(
            429,
            {"error": {"message": "quota exceeded"}},
        )

        result = generate_response("Return JSON.")

        self.assertEqual(result["error"], "Gemini rate limit reached.")


class ResearchLoopTests(unittest.TestCase):
    @patch("agent.research.generate_response")
    @patch("agent.research.fetch_page")
    @patch("agent.research.web_search")
    def test_loop_fetches_and_only_cites_fetched_urls(
        self,
        mock_search: Mock,
        mock_fetch: Mock,
        mock_generate: Mock,
    ) -> None:
        mock_search.return_value = {
            "query": "python",
            "results": [{"title": "Python", "url": "https://example.com", "snippet": "info"}],
        }
        mock_fetch.return_value = {
            "url": "https://example.com",
            "title": "Python",
            "content": "Python content.",
        }
        mock_generate.side_effect = [
            {"text": '{"action":"search","arguments":{"query":"python"}}', "usage": {}},
            {"text": '{"action":"fetch","arguments":{"url":"https://example.com"}}', "usage": {}},
            {
                "text": (
                    '{"action":"finish","arguments":{"summary":"Answer",'
                    '"sources":["https://example.com","https://invented.example"]}}'
                ),
                "usage": {},
            },
        ]

        result = run_research("What is Python?")

        self.assertEqual(result, {"summary": "Answer", "sources": ["https://example.com"]})

    @patch("agent.research.generate_response")
    def test_malformed_tool_call_returns_error(self, mock_generate: Mock) -> None:
        mock_generate.return_value = {"text": '{"action":"unknown","arguments":{}}', "usage": {}}

        result = run_research("Question")

        self.assertEqual(result["error"], "Gemini returned a malformed tool call.")

    @patch("agent.research.generate_response")
    def test_llm_failure_becomes_error(self, mock_generate: Mock) -> None:
        mock_generate.return_value = {"error": "Gemini request failed.", "text": ""}

        result = run_research("Question")

        self.assertEqual(result["error"], "Gemini request failed.")
