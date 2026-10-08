# Tool-Using Research Agent

## Objective

The Tool-Using Research Agent will answer research questions by using external
tools and citing the sources it fetches.

## Current development stage

This repository is currently at **Part 01 - Project Foundation**. It contains
only the basic Python project structure and a minimal health check. No agent
logic, search API integration, LLM integration, citations, or LangGraph
workflow has been implemented yet.

## Planned architecture

The project is expected to grow into the following high-level components:

1. An application entry point for receiving research questions.
2. An agent orchestration layer that decides when external tools are needed.
3. Tool integrations for fetching relevant research sources.
4. A response layer that summarizes findings and cites fetched sources.
5. Tests covering the agent, tools, and response behavior.

These components are planned only; they are intentionally not part of the
current implementation.

## Requirements

- Python 3.11 or newer

## Installation

Create and activate a virtual environment, then install the current
requirements:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

There are no third-party dependencies in this stage.

## Run the current version

From the project root, run:

```powershell
python -m app.main
```

Expected output:

```text
Tool-Using Research Agent foundation is working.
```
