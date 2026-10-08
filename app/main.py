"""Entry point for the Tool-Using Research Agent."""

import argparse

from agent.research import run_research


def main() -> None:
    """Run the foundation health check or a bounded research question."""
    parser = argparse.ArgumentParser()
    parser.add_argument("question", nargs="?", help="Research question to investigate")
    args = parser.parse_args()
    if args.question:
        print(run_research(args.question))
        return
    print("Tool-Using Research Agent foundation is working.")


if __name__ == "__main__":
    main()
