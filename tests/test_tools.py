"""Tests for external tools."""

import os
import unittest
from unittest.mock import Mock, patch

import requests
import httpx

from app.tools import MAX_PAGE_CONTENT_LENGTH, fetch_page, web_search


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


class FetchPageTests(unittest.TestCase):
    @patch("app.tools.httpx.get")
    def test_valid_page_returns_title_and_readable_content(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.text = """
            <html><head><title>Example page</title><style>hidden</style></head>
            <body><h1>Heading</h1><p>Readable content.</p>
            <script>secret = true</script></body></html>
        """
        mock_get.return_value = mock_response

        result = fetch_page("https://example.com/page")

        self.assertEqual(result["url"], "https://example.com/page")
        self.assertEqual(result["title"], "Example page")
        self.assertEqual(result["content"], "Heading Readable content.")
        self.assertNotIn("error", result)
        mock_response.raise_for_status.assert_called_once_with()

    @patch("app.tools.httpx.get")
    def test_invalid_url_returns_error_without_request(self, mock_get: Mock) -> None:
        result = fetch_page("not-a-url")

        self.assertEqual(result["content"], "")
        self.assertIn("error", result)
        mock_get.assert_not_called()

    @patch("app.tools.httpx.get", side_effect=httpx.TimeoutException("slow response"))
    def test_timeout_returns_error(self, mock_get: Mock) -> None:
        result = fetch_page("https://example.com")

        self.assertEqual(result["error"], "Page request timed out.")
        self.assertEqual(result["content"], "")
        mock_get.assert_called_once()

    @patch("app.tools.httpx.get")
    def test_http_error_returns_error(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "not found",
            request=httpx.Request("GET", "https://example.com"),
            response=httpx.Response(404),
        )
        mock_get.return_value = mock_response

        result = fetch_page("https://example.com")

        self.assertEqual(result["error"], "Page returned an HTTP error.")
        self.assertEqual(result["content"], "")

    @patch("app.tools.httpx.get")
    def test_empty_page_returns_error(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.text = "<html><body> </body></html>"
        mock_get.return_value = mock_response

        result = fetch_page("https://example.com/empty")

        self.assertEqual(result["error"], "Page did not contain readable content.")

    @patch("app.tools._parse_page", side_effect=ValueError("malformed HTML"))
    @patch("app.tools.httpx.get")
    def test_parsing_failure_returns_error(
        self,
        mock_get: Mock,
        mock_parse_page: Mock,
    ) -> None:
        mock_response = Mock()
        mock_response.text = "<html>"
        mock_get.return_value = mock_response

        result = fetch_page("https://example.com/malformed")

        self.assertEqual(result["error"], "Page could not be parsed.")
        mock_parse_page.assert_called_once_with("<html>")

    @patch("app.tools.httpx.get")
    def test_page_content_is_limited(self, mock_get: Mock) -> None:
        mock_response = Mock()
        mock_response.text = f"<p>{'x' * (MAX_PAGE_CONTENT_LENGTH + 100)}</p>"
        mock_get.return_value = mock_response

        result = fetch_page("https://example.com/large")

        self.assertEqual(len(result["content"]), MAX_PAGE_CONTENT_LENGTH)
