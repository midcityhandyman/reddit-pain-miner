"""Render ranked clusters as a markdown or JSON report."""
from __future__ import annotations

import json

from .models import Cluster

MAX_QUOTE_CHARS = 160


def short_quote(text: str, limit: int = MAX_QUOTE_CHARS) -> str:
    """Trim a quote to the limit on a word boundary."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[: limit - 3].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "..."


def pick_quotes(cluster: Cluster, count: int) -> list:
    """Strongest statements first, preferring one quote per source before repeats."""
    seen: set[str] = set()
    first, rest = [], []
    for statement in cluster.statements:
        (rest if statement.source_id in seen else first).append(statement)
        seen.add(statement.source_id)
    return (first + rest)[:count]


def _summary(clusters: list[Cluster], top: int, quotes: int) -> list[dict]:
    rows = []
    for rank, cluster in enumerate(clusters[:top], start=1):
        rule_counts: dict[str, int] = {}
        for statement in cluster.statements:
            for reason in statement.reasons:
                rule_counts[reason] = rule_counts.get(reason, 0) + 1
        signals = sorted(rule_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        rows.append({
            "rank": rank,
            "label": cluster.label,
            "rank_score": cluster.rank_score,
            "mentions": cluster.mentions,
            "threads": cluster.thread_count,
            "authors": cluster.author_count,
            "top_signals": [name for name, _ in signals],
            "quotes": [
                {"text": short_quote(s.text), "score": s.score, "source": s.source_id, "upvotes": s.upvotes}
                for s in pick_quotes(cluster, quotes)
            ],
        })
    return rows


def render_json(topic: str, thread_count: int, statement_count: int,
                clusters: list[Cluster], top: int = 10, quotes: int = 3) -> str:
    return json.dumps({
        "topic": topic,
        "threads_scanned": thread_count,
        "complaint_statements": statement_count,
        "clusters_found": len(clusters),
        "pain_points": _summary(clusters, top, quotes),
    }, indent=2)


def render_markdown(topic: str, thread_count: int, statement_count: int,
                    clusters: list[Cluster], top: int = 10, quotes: int = 3) -> str:
    lines = [
        f"# Pain point report: {topic}",
        "",
        f"- Threads scanned: {thread_count}",
        f"- Complaint statements kept: {statement_count}",
        f"- Clusters found: {len(clusters)} (showing top {min(top, len(clusters))})",
        "",
    ]
    if not clusters:
        lines.append("No complaint statements cleared the score threshold.")
        return "\n".join(lines) + "\n"
    lines += ["| Rank | Pain point | Score | Mentions | Threads | Authors |",
              "| --- | --- | --- | --- | --- | --- |"]
    rows = _summary(clusters, top, quotes)
    for row in rows:
        lines.append(
            f"| {row['rank']} | {row['label']} | {row['rank_score']:.2f} | {row['mentions']} "
            f"| {row['threads']} | {row['authors']} |"
        )
    for row in rows:
        lines += ["", f"## {row['rank']}. {row['label']}", "",
                  f"Signals: {', '.join(row['top_signals'])}", ""]
        for quote in row["quotes"]:
            lines.append(
                f"- \"{quote['text']}\" (score {quote['score']:.2f}, "
                f"{quote['upvotes']} upvotes, source {quote['source']})"
            )
    return "\n".join(lines) + "\n"
