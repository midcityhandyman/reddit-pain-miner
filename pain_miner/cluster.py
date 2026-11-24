"""Deterministic clustering of complaint statements.

TF-IDF vectors over lightly stemmed tokens, grouped with leader clustering:
each statement joins the most similar existing cluster if cosine similarity to
its centroid clears a threshold, otherwise it starts a new cluster. A second
pass reassigns every statement to its nearest final centroid. No randomness,
no third party dependencies.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .models import Cluster, Statement

STOPWORDS = frozenset(
    """a about after again all also always am an and any are as at be because been being but by can
    cannot could did do does doing done down each even ever every for from get gets getting got had
    has have having he her here him his how i if in into is it its just like literally me more most
    much my never no not now of off on once one only or other our out over really so some still
    such than that the their them then there these they thing things this those to too up us very
    was we were what when where which while who why will with would you your don't doesn't can't
    won't isn't i'm i've it's that's tool tools app software use using used""".split()
)

Vector = dict[str, float]


_ES_BASES = ("s", "x", "z", "ch", "sh")


def stem(token: str) -> str:
    """Crude suffix stripper. Plural and singular must land on the same stem."""
    for suffix, replacement in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        base = token[: len(token) - len(suffix)]
        if not token.endswith(suffix) or len(base) < 3:
            continue
        if suffix == "es" and not base.endswith(_ES_BASES):
            continue  # "invoices" is "invoice" + "s", not "invoic" + "es"
        if suffix == "s" and base.endswith("s"):
            continue  # leave "address", "less" alone
        return base + replacement
    return token


def tokenize(text: str) -> list[tuple[str, str]]:
    """Return (stem, surface form) pairs for the content words in text."""
    pairs = []
    for word in re.findall(r"[a-z][a-z']+", text.lower().replace("’", "'")):
        if word in STOPWORDS or len(word) < 3:
            continue
        pairs.append((stem(word.replace("'", "")), word))
    return pairs


def _normalize(vector: Vector) -> Vector:
    norm = math.sqrt(sum(v * v for v in vector.values()))
    return {k: v / norm for k, v in vector.items()} if norm else {}


def cosine(a: Vector, b: Vector) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(value * b.get(term, 0.0) for term, value in a.items())


def tfidf_vectors(token_lists: list[list[str]]) -> list[Vector]:
    doc_freq: Counter[str] = Counter()
    for tokens in token_lists:
        doc_freq.update(set(tokens))
    total = len(token_lists)
    vectors = []
    for tokens in token_lists:
        counts = Counter(tokens)
        vectors.append(_normalize({
            term: count * (math.log((1 + total) / (1 + doc_freq[term])) + 1.0)
            for term, count in counts.items()
        }))
    return vectors


def _centroid(vectors: list[Vector]) -> Vector:
    summed: Vector = {}
    for vector in vectors:
        for term, value in vector.items():
            summed[term] = summed.get(term, 0.0) + value
    return _normalize(summed)


def _nearest(vector: Vector, centroids: list[Vector]) -> tuple[int, float]:
    best_index, best_sim = -1, -1.0
    for index, centroid in enumerate(centroids):
        sim = cosine(vector, centroid)
        if sim > best_sim:
            best_index, best_sim = index, sim
    return best_index, best_sim


def rank_score(statements: list[Statement]) -> float:
    """Total complaint score, boosted when several distinct authors agree."""
    authors = len({s.author for s in statements})
    return round(sum(s.score for s in statements) * math.log2(1 + authors), 2)


def cluster_statements(statements: list[Statement], similarity: float = 0.15) -> list[Cluster]:
    """Group statements into ranked clusters. Input order decides the seeds."""
    if not statements:
        return []
    token_pairs = [tokenize(s.text) for s in statements]
    vectors = tfidf_vectors([[stem_ for stem_, _ in pairs] for pairs in token_pairs])

    members: list[list[int]] = []
    centroids: list[Vector] = []
    for index, vector in enumerate(vectors):
        best, sim = _nearest(vector, centroids)
        if best >= 0 and sim >= similarity:
            members[best].append(index)
            centroids[best] = _centroid([vectors[i] for i in members[best]])
        else:
            members.append([index])
            centroids.append(vector)

    # Reassignment pass: fixes early statements that fit a later cluster better.
    # A statement that resembles nothing (similarity 0, for example all stopwords)
    # stays where it was seeded instead of falling into the first cluster.
    seeded = {index: group for group, indexes in enumerate(members) for index in indexes}
    reassigned: list[list[int]] = [[] for _ in centroids]
    for index, vector in enumerate(vectors):
        best, sim = _nearest(vector, centroids)
        reassigned[best if sim > 0.0 else seeded[index]].append(index)

    surface: dict[str, Counter[str]] = {}
    for pairs in token_pairs:
        for stem_, word in pairs:
            surface.setdefault(stem_, Counter())[word] += 1

    clusters = []
    for group in reassigned:
        if not group:
            continue
        centroid = _centroid([vectors[i] for i in group])
        top_terms = sorted(centroid.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
        label = " / ".join(
            sorted(surface[t].items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for t, _ in top_terms
        ) or "misc"
        items = sorted((statements[i] for i in group), key=lambda s: (-s.score, s.source_id, s.text))
        clusters.append(Cluster(label=label, statements=items, rank_score=rank_score(items)))
    clusters.sort(key=lambda c: (-c.rank_score, c.label))
    return clusters
