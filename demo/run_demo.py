"""Offline demo: replays the synthetic fixture and prints the ranked report.

    python demo/run_demo.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pain_miner.cli import build_report  # noqa: E402
from pain_miner.client import FixtureArchiveClient, fetch_threads  # noqa: E402
from pain_miner.extract import extract_statements  # noqa: E402

TOPIC = "invoicing software"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", newline=chr(10))
    client = FixtureArchiveClient(ROOT / "fixtures")
    print("== reddit-pain-miner offline demo ==")
    print(f"topic: {TOPIC} | source: fixtures/invoicing_software.json (synthetic) | network calls: 0")
    print()
    print("-- strongest complaint statements and the rules that fired --")
    for statement in extract_statements(fetch_threads(client, TOPIC))[:5]:
        print(f"{statement.score:5.2f}  [{', '.join(statement.reasons)}]")
        print(f"       {statement.text}")
    print()
    print("-- ranked report --")
    sys.stdout.write(build_report(client, TOPIC, top=6, quotes=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
