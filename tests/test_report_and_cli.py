import json

from pain_miner.cli import build_report, load_dotenv, main
from pain_miner.cluster import cluster_statements
from pain_miner.models import Cluster, Statement
from pain_miner.report import MAX_QUOTE_CHARS, pick_quotes, render_markdown, short_quote

TOPIC = "invoicing software"


def test_short_quote_trims_on_word_boundary():
    long_text = "word " * 100
    quote = short_quote(long_text)
    assert len(quote) <= MAX_QUOTE_CHARS and quote.endswith("word...")
    assert short_quote("short   text") == "short text"


def test_pick_quotes_prefers_distinct_sources():
    def s(text, source):
        return Statement(text=text, score=3.0, reasons=(), thread_id="p", source_id=source, author="a")
    cluster = Cluster(label="x", statements=[s("one", "p1"), s("two", "p1"), s("three", "c1")])
    assert [q.text for q in pick_quotes(cluster, 2)] == ["one", "three"]


def test_empty_report_says_so():
    assert "No complaint statements" in render_markdown("nothing", 0, 0, cluster_statements([]))


def test_end_to_end_report_from_fixtures(fixture_client):
    data = json.loads(build_report(fixture_client, TOPIC, fmt="json", top=4))
    assert data["threads_scanned"] == 7 and data["complaint_statements"] > 30
    labels = [p["label"] for p in data["pain_points"]]
    assert len(labels) == 4
    for theme in ("bank", "reminders", "receipts", "price"):
        assert any(theme in label for label in labels), (theme, labels)
    scores = [p["rank_score"] for p in data["pain_points"]]
    assert scores == sorted(scores, reverse=True)
    for point in data["pain_points"]:
        assert point["threads"] >= 2 and 1 <= len(point["quotes"]) <= 3
        assert all(len(q["text"]) <= MAX_QUOTE_CHARS for q in point["quotes"])


def test_report_does_not_leak_usernames(fixture_client):
    assert "sample_user" not in build_report(fixture_client, TOPIC)


def test_cli_offline_writes_markdown(tmp_path, capsys):
    out = tmp_path / "report.md"
    assert main(["--topic", TOPIC, "--offline", "--out", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Pain point report: invoicing software")
    assert "| Rank | Pain point |" in text


def test_cli_live_mode_needs_base_url(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("PAIN_MINER_API_BASE", raising=False)
    monkeypatch.chdir(tmp_path)
    assert main(["--topic", TOPIC]) == 2
    assert "PAIN_MINER_API_BASE" in capsys.readouterr().err


def test_cli_unknown_offline_topic_fails_cleanly(capsys):
    assert main(["--topic", "quantum toasters", "--offline"]) == 1
    assert "no fixture recorded" in capsys.readouterr().err


def test_load_dotenv_keeps_existing_values(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comment\nPM_TEST_A=from_file\nPM_TEST_B='quoted'\n", encoding="utf-8")
    monkeypatch.setenv("PM_TEST_A", "from_env")
    monkeypatch.delenv("PM_TEST_B", raising=False)
    load_dotenv(env)
    import os
    assert os.environ["PM_TEST_A"] == "from_env" and os.environ["PM_TEST_B"] == "quoted"
    monkeypatch.delenv("PM_TEST_B")
