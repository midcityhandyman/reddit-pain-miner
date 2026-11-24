"""Rule based complaint extraction.

Each sentence is scored by a small set of weighted patterns. A sentence must
trigger at least one complaint rule to be kept; modifiers (intensity, first
person, upvotes) only adjust a score that already exists. Every kept statement
carries the names of the rules that fired, so a score can always be explained.
"""
from __future__ import annotations

import math
import re
from typing import Iterable

from .models import Statement, Thread

_F = re.IGNORECASE

# (rule name, weight, pattern)
COMPLAINT_RULES: list[tuple[str, float, re.Pattern[str]]] = [
    ("strong_negative", 3.0, re.compile(
        r"\b(hate[sd]?|can'?t stand|cannot stand|sick of|tired of|fed up|worst)\b", _F)),
    ("frustration", 3.0, re.compile(
        r"\b(frustrat\w+|annoy\w+|infuriat\w+|nightmare|painful|headache|drives me (nuts|crazy|up the wall))\b", _F)),
    ("malfunction", 2.5, re.compile(
        r"\b(broken|breaks|buggy|crash\w*|fail(s|ed|ing)?|glitch\w*|unusable|useless|"
        r"(doesn'?t|does not|never|stopped) work(s|ing)?)\b", _F)),
    ("cost", 2.5, re.compile(
        r"\b(too expensive|overpriced|price (hike|increase)|hidden fees?|rip-?off|costs? too much|"
        r"(raised|doubled|tripled) (the |their )?(price|prices|pricing))\b", _F)),
    ("friction", 2.0, re.compile(
        r"\b(waste[sd]? (of )?(time|money|hours)|wasting|takes forever|(too|so|painfully) slow|"
        r"manually|by hand|tedious|clunky|confusing|hours every)\b", _F)),
    ("unmet_need", 2.0, re.compile(
        r"\b(i wish|wish (it|they|there)|if only|why (can'?t|doesn'?t|isn'?t|is there no)|"
        r"is there (a|an|any) (tool|app|way)|looking for (a|an|any)? ?alternative|"
        r"switch(ed|ing)? away|cancel(ed|led|ing|ling))\b", _F)),
    ("support", 2.0, re.compile(
        r"\b(support (never|took|ignored|is useless|was useless)|no (response|reply)|still waiting)\b", _F)),
    ("limitation", 1.5, re.compile(
        r"\b(no way to|can'?t|cannot|won'?t let|doesn'?t (let|support|have|allow)|missing|lacks?)\b", _F)),
]

INTENSIFIER = re.compile(
    r"\b(so|really|extremely|absolutely|constantly|always|every single|again|still|literally)\b", _F)
FIRST_PERSON = re.compile(r"\b(i|i'm|i've|my|me|we|our|us)\b", _F)
SHOUTING = re.compile(r"\b[A-Z]{4,}\b|!!")
POSITIVE = re.compile(
    r"\b(love|great|awesome|works (well|fine|perfectly)|happy with|recommend|solved|no complaints)\b", _F)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
MIN_WORDS = 4
DEFAULT_MIN_SCORE = 2.5


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, dropping quoted lines (markdown '>' prefix)."""
    kept_lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith(">")]
    parts = _SENTENCE_SPLIT.split("\n".join(kept_lines))
    return [re.sub(r"\s+", " ", p).strip() for p in parts if p and p.strip()]


def score_sentence(sentence: str, upvotes: int = 0) -> tuple[float, tuple[str, ...]]:
    """Return (score, rule names). Score is 0.0 when no complaint rule fires."""
    if len(sentence.split()) < MIN_WORDS:
        return 0.0, ()
    score = 0.0
    reasons: list[str] = []
    for name, weight, pattern in COMPLAINT_RULES:
        if pattern.search(sentence):
            score += weight
            reasons.append(name)
    if not reasons:
        return 0.0, ()
    if INTENSIFIER.search(sentence):
        score += 0.5
        reasons.append("intensifier")
    if FIRST_PERSON.search(sentence):
        score += 0.5
        reasons.append("first_person")
    if SHOUTING.search(sentence):
        score += 0.5
        reasons.append("shouting")
    if POSITIVE.search(sentence):
        score -= 2.0
        reasons.append("positive_dampener")
    if upvotes > 0:
        score += min(1.5, 0.5 * math.log10(1 + upvotes))
    return round(max(score, 0.0), 2), tuple(reasons)


def _sources(thread: Thread) -> Iterable[tuple[str, str, str, int]]:
    post = thread.post
    yield post.id, f"{post.title}.\n{post.body}", post.author, post.score
    for comment in thread.comments:
        yield comment.id, comment.body, comment.author, comment.score


def extract_statements(threads: Iterable[Thread], min_score: float = DEFAULT_MIN_SCORE) -> list[Statement]:
    """Extract complaint statements from threads, strongest first, without duplicates."""
    statements: list[Statement] = []
    seen: set[str] = set()
    for thread in threads:
        for source_id, text, author, upvotes in _sources(thread):
            for sentence in split_sentences(text):
                score, reasons = score_sentence(sentence, upvotes)
                key = sentence.lower()
                if score < min_score or key in seen:
                    continue
                seen.add(key)
                statements.append(
                    Statement(
                        text=sentence,
                        score=score,
                        reasons=reasons,
                        thread_id=thread.post.id,
                        source_id=source_id,
                        author=author,
                        upvotes=upvotes,
                    )
                )
    statements.sort(key=lambda s: (-s.score, s.source_id, s.text))
    return statements
