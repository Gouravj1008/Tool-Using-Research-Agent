# Tool-Using Research Agent

## Objective

The Tool-Using Research Agent will answer research questions by using external
tools and citing the sources it fetches.

## Current development stage

This repository is currently at **Part 03 - Fetch Page Tool**. It contains the
basic project foundation, an independent `web_search(query)` tool, and an
independent `fetch_page(url)` tool. Agent planning, LangGraph, summarization,
citation validation, LLM integration, and final answer generation have not
been implemented yet.

## Planned architecture

The project is expected to grow into the following high-level components:

1. An application entry point for receiving research questions.
2. An agent orchestration layer that decides when external tools are needed.
3. Tool integrations for web search and fetching relevant research sources.
4. A response layer that summarizes findings and cites fetched sources.
5. Tests covering the agent, tools, and response behavior.

Only the web search and page fetching components are implemented in the current
stage. The remaining components are planned only.

## Requirements

- Python 3.11 or newer
- A Brave Search API key

## Installation

Create and activate a virtual environment, then install the current
requirements:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The current tools use `requests` and `httpx` for HTTPS requests, plus
BeautifulSoup for HTML parsing. Copy
`.env.example` to `.env` and set the key used by the Brave Search API:

```text
BRAVE_SEARCH_API_KEY=your_brave_search_api_key
```

The application reads this variable from the process environment. Loading a
`.env` file is intentionally not implemented yet; export the variable in your
shell or configure it through your runtime environment.

## Web search tool

`app.tools.web_search(query)` calls the Brave Search API and returns a stable
structured result:

```python
{
    "query": "python 3.11 release",
    "results": [
        {
            "title": "What’s New In Python 3.11",
            "url": "https://docs.python.org/3.11/whatsnew/3.11.html",
            "snippet": "Summary of new features in Python 3.11."
        }
    ]
}
```

Invalid input, missing configuration, provider failures, timeouts, and empty
results return an empty `results` list with an explanatory `error` or
`message` field instead of crashing the application.

## Page fetching tool

`app.tools.fetch_page(url)` fetches an HTTP(S) page and returns readable text:

```python
{
    "url": "https://example.com",
    "title": "Example Domain",
    "content": "Example Domain This domain is for use in illustrative examples..."
}
```

The tool removes common non-readable elements such as scripts and styles,
normalizes whitespace, and limits returned content to 50,000 characters.
Invalid URLs, timeouts, HTTP errors, empty pages, request failures, and parsing
failures return an explanatory `error` field without raising to the caller.

Example usage:

```powershell
python -c "from app.tools import fetch_page; print(fetch_page('https://example.com'))"
```

Expected shape:

```python
{
    "url": "https://example.com",
    "title": "Example Domain",
    "content": "Example Domain This domain is for use in illustrative examples..."
}
```

## Run the current version

From the project root, run:

```powershell
python -m app.main
```

Expected output:

```text
Tool-Using Research Agent foundation is working.
```

## Known limitations

- Results depend on the Brave Search API and require a valid API key.
- The tool currently uses a fixed 10-second request timeout.
- Provider-specific normalization currently supports Brave Search only.
- Page fetching uses a fixed 10-second timeout and a 50,000-character content
  limit.
- There is no retry, caching, ranking, summarization, or citation validation
  yet.
