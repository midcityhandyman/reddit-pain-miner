import json
import urllib.parse

import pytest

from pain_miner.client import (ArchiveError, HttpArchiveClient, fetch_threads, parse_comments,
                               parse_posts, topic_slug)

TOPIC = "invoicing software"


def test_fixture_client_replays_threads_offline(fixture_client):
    threads = fetch_threads(fixture_client, TOPIC)
    assert len(threads) == 7
    assert all(t.comments for t in threads)
    assert threads[0].post.subreddit == "smallbiz_sample"


def test_fixture_client_filters_and_limits(fixture_client):
    assert fixture_client.search_posts(TOPIC, subreddit="other_sub") == []
    assert len(fixture_client.search_posts(TOPIC, limit=2)) == 2


def test_fixture_client_unknown_topic_names_available(fixture_client):
    with pytest.raises(ArchiveError, match="invoicing_software"):
        fixture_client.search_posts("quantum toasters")


def test_topic_slug():
    assert topic_slug("  Invoicing Software! ") == "invoicing_software"


def test_parsers_skip_bad_rows():
    posts = parse_posts({"data": [{"id": "a", "title": "t", "score": "7"}, {"title": "no id"}, "junk"]})
    assert [p.id for p in posts] == ["a"] and posts[0].score == 7
    comments = parse_comments(
        {"data": [{"id": "c1", "body": "[deleted]"}, {"id": "c2", "body": "hello"}]}, "a")
    assert [c.id for c in comments] == ["c2"] and comments[0].post_id == "a"
    with pytest.raises(ArchiveError):
        parse_posts({"data": "nope"})


def test_http_client_builds_urls_and_parses_without_network():
    calls = []

    def fake_opener(url, user_agent, timeout):
        calls.append((url, user_agent))
        if "/api/posts/search" in url:
            return json.dumps({"data": [{"id": "p9", "subreddit": "s", "title": "T", "selftext": "B"}]}).encode()
        return json.dumps({"data": [{"id": "c9", "body": "I hate this", "author": "sample_user_99"}]}).encode()

    client = HttpArchiveClient("https://archive.example.com/", user_agent="test-agent", opener=fake_opener)
    threads = fetch_threads(client, "invoicing software", subreddit="s", limit=5)
    assert threads[0].post.body == "B" and threads[0].comments[0].id == "c9"
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(calls[0][0]).query)
    assert query == {"query": ["invoicing software"], "subreddit": ["s"], "limit": ["5"], "sort": ["desc"]}
    assert calls[0][0].startswith("https://archive.example.com/api/posts/search?")
    assert "link_id=p9" in calls[1][0] and calls[1][1] == "test-agent"


def test_http_client_wraps_failures():
    def broken(url, user_agent, timeout):
        raise OSError("connection refused")

    with pytest.raises(ArchiveError, match="connection refused"):
        HttpArchiveClient("https://archive.example.com", opener=broken).search_posts("x")
    with pytest.raises(ArchiveError):
        HttpArchiveClient("ftp://archive.example.com")
