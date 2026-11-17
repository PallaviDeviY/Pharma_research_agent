from __future__ import annotations

import argparse
import json

import uvicorn

from pharma_intelligence.agents.research_agent import DRUGS, ResearchAgent
from pharma_intelligence.config import settings
from pharma_intelligence.database.queries import ResearchDatabase
from pharma_intelligence.ingestion.pipeline import import_raw, ingest


def main() -> None:
    parser = argparse.ArgumentParser(prog="pharma-intelligence")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("serve", help="Start the local research interface")
    subparsers.add_parser("status", help="Show the local database counts")
    ingestion = subparsers.add_parser("ingest", help="Fetch the controlled drug scope from public APIs")
    ingestion.add_argument("--drug", action="append", choices=sorted(DRUGS), help="Repeat to select drugs; defaults to all four")
    raw = subparsers.add_parser("import-raw", help="Replay downloaded source files from data/raw without network calls")
    raw.add_argument("--drug", action="append", choices=sorted(DRUGS), help="Repeat to select drugs; defaults to all four")
    ask = subparsers.add_parser("ask", help="Ask a research question")
    ask.add_argument("question")
    args = parser.parse_args()

    if args.command == "serve":
        uvicorn.run("pharma_intelligence.api:app", host="127.0.0.1", port=8000, reload=False)
        return
    database = ResearchDatabase(settings.database_path)
    try:
        if args.command == "status":
            print(json.dumps(database.counts(), indent=2))
        elif args.command == "ingest":
            drugs = args.drug or list(DRUGS)
            print(json.dumps(ingest(database, drugs), indent=2))
        elif args.command == "import-raw":
            drugs = args.drug or list(DRUGS)
            print(json.dumps(import_raw(database, drugs), indent=2))
        elif args.command == "ask":
            print(json.dumps(ResearchAgent(database).ask(args.question), indent=2, ensure_ascii=False))
    finally:
        database.close()


if __name__ == "__main__":
    main()

