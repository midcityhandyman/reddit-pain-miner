"""Command line entry point: python -m pain_miner --topic "..." --offline"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .client import ArchiveClient, ArchiveError, FixtureArchiveClient, HttpArchiveClient, fetch_threads
from .cluster import cluster_statements
from .extract import DEFAULT_MIN_SCORE, extract_statements
from .report import render_json, render_markdown

DEFAULT_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, existing environment wins."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def build_report(client: ArchiveClient, topic: str, subreddit: str | None = None, limit: int = 25,
                 min_score: float = DEFAULT_MIN_SCORE, similarity: float = 0.15, top: int = 10,
                 quotes: int = 3, fmt: str = "md") -> str:
    """Run the whole pipeline against any ArchiveClient and return the report text."""
    threads = fetch_threads(client, topic, subreddit=subreddit, limit=limit)
    statements = extract_statements(threads, min_score=min_score)
    clusters = cluster_statements(statements, similarity=similarity)
    render = render_json if fmt == "json" else render_markdown
    return render(topic, len(threads), len(statements), clusters, top=top, quotes=quotes)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pain_miner", description=__doc__)
    parser.add_argument("--topic", required=True, help="search phrase, for example 'invoicing software'")
    parser.add_argument("--subreddit", help="restrict to one subreddit")
    parser.add_argument("--limit", type=int, default=25, help="max threads to pull (default 25)")
    parser.add_argument("--offline", action="store_true", help="replay recorded fixtures, no network")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES, help="fixture directory")
    parser.add_argument("--min-score", type=float, default=DEFAULT_MIN_SCORE)
    parser.add_argument("--similarity", type=float, default=0.15, help="cluster join threshold, 0 to 1")
    parser.add_argument("--top", type=int, default=10, help="pain points to show")
    parser.add_argument("--quotes", type=int, default=3, help="quotes per pain point")
    parser.add_argument("--format", choices=("md", "json"), default="md", dest="fmt")
    parser.add_argument("--out", type=Path, help="write the report here instead of stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    load_dotenv(Path.cwd() / ".env")
    try:
        if args.offline:
            client: ArchiveClient = FixtureArchiveClient(args.fixtures)
        else:
            base_url = os.environ.get("PAIN_MINER_API_BASE", "")
            if not base_url:
                print("error: set PAIN_MINER_API_BASE for live mode, or pass --offline", file=sys.stderr)
                return 2
            client = HttpArchiveClient(
                base_url, user_agent=os.environ.get("PAIN_MINER_USER_AGENT", "reddit-pain-miner/0.1"))
        report = build_report(client, args.topic, args.subreddit, args.limit, args.min_score,
                              args.similarity, args.top, args.quotes, args.fmt)
    except ArchiveError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.out:
        args.out.write_text(report, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(report)
    return 0
