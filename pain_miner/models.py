"""Plain data records passed between pipeline stages."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Post:
    id: str
    subreddit: str
    title: str
    body: str
    author: str
    score: int = 0
    created_utc: int = 0


@dataclass(frozen=True)
class Comment:
    id: str
    post_id: str
    body: str
    author: str
    score: int = 0


@dataclass(frozen=True)
class Thread:
    post: Post
    comments: tuple[Comment, ...] = ()


@dataclass(frozen=True)
class Statement:
    """One complaint sentence with the rules that fired on it."""

    text: str
    score: float
    reasons: tuple[str, ...]
    thread_id: str
    source_id: str
    author: str
    upvotes: int = 0


@dataclass
class Cluster:
    label: str
    statements: list[Statement] = field(default_factory=list)
    rank_score: float = 0.0

    @property
    def mentions(self) -> int:
        return len(self.statements)

    @property
    def thread_count(self) -> int:
        return len({s.thread_id for s in self.statements})

    @property
    def author_count(self) -> int:
        return len({s.author for s in self.statements})
