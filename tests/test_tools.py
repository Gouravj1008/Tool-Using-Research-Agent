"""Tests for external tools."""

import os
import unittest
from unittest.mock import Mock, patch

import requests

from app.tools import web_search


class WebSearchTests(unittest.TestCase):
    @patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-key"})
    @patch("app.tools.requests.get")
    def test_valid_search_returns_normalized_results(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Example result",
                        "url": "https://example.com",
                        "description": "An example snippet.",
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        result = web_search("python testing")

        self.assertEqual(result, {
            "query": "python testing",
            "results": [
                {
                    "title": "Example result",
                    "url": "https://example.com",
                    "snippet": "An example snippet.",
                }
            ],
        })
        mock_get.assert_called_once()
        mock_response.raise_for_status.assert_called_once_with()

    @patch("app.tools.requests.get")
    def test_empty_query_returns_error_without_request(self, mock_get: Mock) -> None:
        result = web_search("  ")

        self.assertEqual(result["query"], "")
        self.assertEqual(result["results"], [])
        self.assertIn("error", result)
        mock_get.assert_not_called()

    @patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-key"})
    @patch("app.tools.requests.get", side_effect=requests.RequestException("offline"))
    def test_failed_request_returns_error(self, mock_get: Mock) -> None:
        result = web_search("python testing")

        self.assertEqual(result["results"], [])
        self.assertEqual(result["error"], "Search provider request failed.")
        mock_get.assert_called_once()

    @patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-key"})
    @patch("app.tools.requests.get", side_effect=requests.Timeout("slow response"))
    def test_timeout_returns_error(self, mock_get: Mock) -> None:
        result = web_search("python testing")

        self.assertEqual(result["results"], [])
        self.assertEqual(result["error"], "Search request timed out.")
        mock_get.assert_called_once()

    @patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-key"})
    @patch("app.tools.requests.get")
    def test_empty_results_returns_message(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.json.return_value = {"web": {"results": []}}
        mock_get.return_value = mock_response

        result = web_search("query with no matches")

        self.assertEqual(result["results"], [])
        self.assertEqual(result["message"], "No search results found.")
