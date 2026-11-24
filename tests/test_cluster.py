from pain_miner.cluster import cluster_statements, cosine, rank_score, stem, tfidf_vectors, tokenize
from pain_miner.models import Statement


def st(text, score=3.0, author="sample_user_01", thread="p1", source=None):
    return Statement(text=text, score=score, reasons=("malfunction",), thread_id=thread,
                     source_id=source or text[:8], author=author)


def test_stem_and_tokenize():
    assert stem("crashes") == "crash" and stem("receipts") == "receipt" and stem("bus") == "bus"
    assert [s for s, _ in tokenize("The app is crashing on my receipts")] == ["crash", "receipt"]


def test_tfidf_vectors_are_unit_length_and_comparable():
    a, b, c = tfidf_vectors([["bank", "sync"], ["bank", "sync", "fail"], ["price", "hike"]])
    assert abs(cosine(a, a) - 1.0) < 1e-9
    assert cosine(a, b) > 0.5 and cosine(a, c) == 0.0


def test_similar_statements_group_and_unrelated_split():
    statements = [
        st("The bank sync fails every week", author="sample_user_01", thread="p1"),
        st("Bank sync is broken again and the bank feed fails", author="sample_user_02", thread="p2"),
        st("They raised the price and the price hike is too expensive", author="sample_user_03"),
        st("Another price hike, too expensive for us", author="sample_user_01"),
        st("The mobile camera crashes on receipts", score=2.6, author="sample_user_04"),
    ]
    clusters = cluster_statements(statements)
    assert sorted(c.mentions for c in clusters) == [1, 2, 2]
    by_label = {c.label: c for c in clusters}
    bank = next(c for label, c in by_label.items() if "bank" in label)
    assert bank.thread_count == 2 and bank.author_count == 2
    assert clusters[-1].mentions == 1  # the singleton ranks last


def test_ranking_rewards_distinct_authors():
    same = [st("a b c d", author="sample_user_01"), st("a b c e", author="sample_user_01")]
    mixed = [st("a b c d", author="sample_user_01"), st("a b c e", author="sample_user_02")]
    assert rank_score(mixed) > rank_score(same)


def test_clustering_is_deterministic_and_handles_empty():
    statements = [st(f"the bank sync fails on day {i}", source=f"s{i}") for i in range(5)]
    first = [(c.label, c.mentions) for c in cluster_statements(statements)]
    assert first == [(c.label, c.mentions) for c in cluster_statements(statements)]
    assert cluster_statements([]) == []
