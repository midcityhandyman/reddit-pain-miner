from pain_miner.extract import extract_statements, score_sentence, split_sentences
from pain_miner.models import Comment, Post, Thread


def make_thread(body, comments=()):
    post = Post(id="p1", subreddit="s", title="A neutral title here", body=body, author="sample_user_01")
    return Thread(post=post, comments=tuple(
        Comment(id=f"c{i}", post_id="p1", body=text, author=f"sample_user_1{i}", score=score)
        for i, (text, score) in enumerate(comments)))


def test_split_sentences_drops_quoted_lines():
    text = "> I hate the quoted part.\nFirst real sentence. Second one!\nThird line"
    assert split_sentences(text) == ["First real sentence.", "Second one!", "Third line"]


def test_neutral_and_short_sentences_score_zero():
    assert score_sentence("How many clients do you have?") == (0.0, ())
    assert score_sentence("Hate it.") == (0.0, ())


def test_rules_fire_and_are_reported():
    score, reasons = score_sentence("I hate sending reminders manually every week")
    assert score == 5.5
    assert reasons == ("strong_negative", "friction", "first_person")


def test_modifiers_never_create_a_complaint_alone():
    assert score_sentence("I really always use my phone for this")[0] == 0.0


def test_positive_dampener_lowers_score():
    plain, _ = score_sentence("The export is missing a date column")
    praised, reasons = score_sentence("The export is missing a date column but otherwise works well")
    assert praised < plain and "positive_dampener" in reasons


def test_upvotes_add_a_capped_bonus():
    base, _ = score_sentence("The sync is broken on the new version")
    liked, _ = score_sentence("The sync is broken on the new version", upvotes=99)
    huge, _ = score_sentence("The sync is broken on the new version", upvotes=10**9)
    assert liked == base + 1.0 and huge == base + 1.5


def test_extract_orders_by_score_and_dedupes():
    thread = make_thread(
        "The sync is broken on the new version. Everything else is fine today.",
        [("I hate that the sync is so buggy and it crashes constantly.", 10),
         ("The sync is broken on the new version.", 3),
         ("What version are you on?", 50)])
    statements = extract_statements([thread])
    assert [s.source_id for s in statements] == ["c0", "p1"]
    assert statements[0].score > statements[1].score
    assert statements[0].thread_id == "p1" and statements[0].author == "sample_user_10"


def test_min_score_threshold_filters():
    thread = make_thread("The report is missing a totals row for now.")
    assert len(extract_statements([thread], min_score=1.0)) == 1
    assert extract_statements([thread], min_score=5.0) == []


def test_typographic_apostrophes_match_the_same_rules():
    straight = score_sentence("The export doesn't work on my phone")
    curly = score_sentence("The export doesn\u2019t work on my phone")
    assert curly == straight and "malfunction" in curly[1]
    assert split_sentences("It can\u2019t export.") == ["It can't export."]
