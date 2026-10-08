# Tool-Using Research Agent

## Objective

The Tool-Using Research Agent will answer research questions by using external
tools and citing the sources it fetches.

## Current development stage

This repository is currently at **Part 04 - Gemini Research Loop**. It contains
the basic project foundation, independent search and page-fetching tools, and a
small manual Gemini decide-act-observe loop. LangGraph and a separate
`summarize_source` tool have not been implemented.

## Planned architecture

The project is expected to grow into the following high-level components:

1. An application entry point for receiving research questions.
2. An agent orchestration layer that decides when external tools are needed.
3. Tool integrations for web search and fetching relevant research sources.
4. A response layer that summarizes findings and cites fetched sources.
5. Tests covering the agent, tools, and response behavior.

Only the web search, page fetching, and manual research loop are implemented in
the current stage. The remaining components are planned only.

## Requirements

- Python 3.11 or newer
- A Brave Search API key
- A Gemini API key

## Installation

Create and activate a virtual environment, then install the current
requirements:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The current tools use `requests` and `httpx` for HTTPS requests, plus
BeautifulSoup for HTML parsing. The Gemini provider uses the official
`google-genai` SDK. Copy
`.env.example` to `.env` and set the key used by the Brave Search API:

```text
BRAVE_SEARCH_API_KEY=your_brave_search_api_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash
```

The application loads these values from `.env` using `python-dotenv`. Never
commit `.env`; it is ignored by Git.

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

`app.tools.fetch(url)` fetches an HTTP(S) page and returns an observation:

```python
{
    "success": True,
    "url": "https://example.com",
    "title": "Example Domain",
    "content": "Example Domain This domain is for use in illustrative examples..."
}
```

The tool uses `trafilatura` to extract readable content and limits it to
50,000 characters. Invalid URLs, timeouts, HTTP errors such as `HTTP 403`,
`HTTP 404`, and `HTTP 500`, empty pages, request failures, and extraction
failures return `success: False` with an explanatory `error` field instead of
raising an exception. The previous `fetch_page(url)` name remains as a
compatibility wrapper.

Example usage:

```powershell
python -c "from app.tools import fetch; print(fetch('https://example.com'))"
```

Expected shape:

```python
{
    "url": "https://example.com",
    "title": "Example Domain",
    "content": "Example Domain This domain is for use in illustrative examples..."
}
```

## Gemini research loop

`agent.llm.generate_response` is the isolated Gemini provider adapter.
`agent.research.run_research(question)` implements a bounded manual
decide-act-observe loop. Gemini returns one JSON action at a time using only
`search`, `fetch`, or `finish`. Tool arguments are validated before execution,
unknown actions are rejected, and final citations are restricted to source IDs
for pages that were actually fetched. A finish call must include at least one
valid fetched source ID; URLs, search-only snippets, and unknown IDs are
rejected.

## Research scratchpad

`agent.scratchpad.Scratchpad` stores structured, bounded findings separately
from the raw conversation. A fetched page is reduced to a compact finding with
its source ID, URL, title, claims, and optional discovery query. The raw page
content is then discarded from active scratchpad context.

Before:

```text
model context = full webpage HTML/text, potentially thousands of characters
```

After:

```text
model context = {"source_id":"a1b2c3d4e5f6","url":"https://example.com",
                 "title":"Example","finding":"Compact finding...",
                 "claims":[],"query":"example"}
```

The scratchpad enforces both a maximum finding count and maximum rendered
context size, evicting the oldest findings when either bound is reached.

Obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
Free-tier availability and quotas are controlled by Google and may change.

## Run the current version

From the project root, run:

```powershell
python -m app.main
```

Expected output:

```text
Tool-Using Research Agent foundation is working.
```

Run a research question:

```powershell
python -m app.main "What are the main benefits of Python 3.11?"
```

The output is a dictionary containing either `summary` and fetched `sources`,
or a non-sensitive `error` message.

## Known limitations

- Results depend on the Brave Search API and require a valid API key.
- The tool currently uses a fixed 10-second request timeout.
- Provider-specific normalization currently supports Brave Search only.
- Page fetching uses a fixed 10-second timeout and a 50,000-character content
  limit.
- Gemini model, quotas, API errors, and rate limits depend on the configured
  Google account and free-tier availability.
- There is no retry, caching, ranking, summarization, or citation validation
  yet.
