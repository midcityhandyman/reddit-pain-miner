"""Archive clients.

The pipeline only knows the ArchiveClient interface. Two implementations:

* HttpArchiveClient talks to a public archive search API over HTTPS.
* FixtureArchiveClient replays recorded payloads from disk, so tests and the
  demo never touch the network.

Both feed the same payload parser, so the offline path exercises the same
parsing code as the live one.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Protocol

from .models import Comment, Post, Thread


class ArchiveError(RuntimeError):
    """Raised when the archive cannot answer a request."""


class ArchiveClient(Protocol):
    def search_posts(self, topic: str, subreddit: str | None = None, limit: int = 25) -> list[Post]:
        ...

    def fetch_comments(self, post_id: str, limit: int = 200) -> list[Comment]:
        ...


def _rows(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        payload = payload.get("data", [])
    if not isinstance(payload, list):
        raise ArchiveError("unexpected payload shape: expected a list under 'data'")
    return [row for row in payload if isinstance(row, dict)]


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def parse_posts(payload: Any) -> list[Post]:
    posts = []
    for row in _rows(payload):
        if not row.get("id"):
            continue
        posts.append(
            Post(
                id=str(row["id"]),
                subreddit=str(row.get("subreddit", "")),
                title=str(row.get("title", "")),
                body=str(row.get("selftext") or row.get("body") or ""),
                author=str(row.get("author", "unknown")),
                score=_int(row.get("score")),
                created_utc=_int(row.get("created_utc")),
            )
        )
    return posts


def parse_comments(payload: Any, post_id: str) -> list[Comment]:
    comments = []
    for row in _rows(payload):
        body = str(row.get("body") or "")
        if not row.get("id") or body in ("", "[deleted]", "[removed]"):
            continue
        comments.append(
            Comment(
                id=str(row["id"]),
                post_id=post_id,
                body=body,
                author=str(row.get("author", "unknown")),
                score=_int(row.get("score")),
            )
        )
    return comments


def _default_opener(url: str, user_agent: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


class HttpArchiveClient:
    """Live client for an archive that exposes posts/search and comments/search."""

    def __init__(
        self,
        base_url: str,
        user_agent: str = "reddit-pain-miner/0.1",
        timeout: float = 20.0,
        opener: Callable[[str, str, float], bytes] | None = None,
    ) -> None:
        if not base_url.lower().startswith(("https://", "http://")):
            raise ArchiveError("base_url must start with http:// or https://")
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self._opener = opener or _default_opener

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        url = f"{self.base_url}{path}?{query}"
        try:
            raw = self._opener(url, self.user_agent, self.timeout)
            return json.loads(raw)
        except (OSError, ValueError) as exc:
            raise ArchiveError(f"archive request failed for {path}: {exc}") from exc

    def search_posts(self, topic: str, subreddit: str | None = None, limit: int = 25) -> list[Post]:
        payload = self._get(
            "/api/posts/search",
            {"query": topic, "subreddit": subreddit, "limit": limit, "sort": "desc"},
        )
        return parse_posts(payload)[:limit]

    def fetch_comments(self, post_id: str, limit: int = 200) -> list[Comment]:
        payload = self._get("/api/comments/search", {"link_id": post_id, "limit": limit})
        return parse_comments(payload, post_id)[:limit]


def topic_slug(topic: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")


class FixtureArchiveClient:
    """Replays recorded payloads from <fixtures_dir>/<topic_slug>.json."""

    def __init__(self, fixtures_dir: str | Path) -> None:
        self.fixtures_dir = Path(fixtures_dir)
        self._comments: dict[str, Any] = {}

    def available_topics(self) -> list[str]:
        return sorted(p.stem for p in self.fixtures_dir.glob("*.json"))

    def search_posts(self, topic: str, subreddit: str | None = None, limit: int = 25) -> list[Post]:
        path = self.fixtures_dir / f"{topic_slug(topic)}.json"
        if not path.is_file():
            known = ", ".join(self.available_topics()) or "none"
            raise ArchiveError(f"no fixture recorded for topic '{topic}' (available: {known})")
        recording = json.loads(path.read_text(encoding="utf-8"))
        self._comments.update(recording.get("comments", {}))
        posts = parse_posts(recording.get("posts", {}))
        if subreddit:
            posts = [p for p in posts if p.subreddit.lower() == subreddit.lower()]
        return posts[:limit]

    def fetch_comments(self, post_id: str, limit: int = 200) -> list[Comment]:
        return parse_comments(self._comments.get(post_id, {"data": []}), post_id)[:limit]


def fetch_threads(
    client: ArchiveClient, topic: str, subreddit: str | None = None, limit: int = 25
) -> list[Thread]:
    threads = []
    for post in client.search_posts(topic, subreddit=subreddit, limit=limit):
        threads.append(Thread(post=post, comments=tuple(client.fetch_comments(post.id))))
    return threads
