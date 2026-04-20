from __future__ import annotations

from datetime import datetime

from almanac.ingest import Commit, FileChange
from almanac.stats import compute_bundle
from almanac.window import Window


def test_compute_bundle_merges_same_author_across_emails():
    commits = [
        Commit(
            sha="1",
            ts="2025-01-01T10:00:00+00:00",
            author_name="Alice Smith",
            author_email="alice@work.com",
            parents=[],
            subject="feat: add thing",
            files=[FileChange("a.py", 4, 1)],
        ),
        Commit(
            sha="2",
            ts="2025-01-02T10:00:00+00:00",
            author_name="Alice Smith",
            author_email="alice@gmail.com",
            parents=[],
            subject="fix: repair thing",
            files=[FileChange("a.py", 3, 2)],
        ),
    ]

    bundle = compute_bundle(
        commits,
        Window(datetime(2025, 1, 1), datetime(2025, 1, 31), "2025-01"),
        {"path": ".", "name": "repo", "head_sha": "abc123"},
        classifier_strategy="rules",
    )

    assert len(bundle["authors"]) == 1
    author = bundle["authors"][0]
    assert author["name"] == "Alice Smith"
    assert author["emails"] == ["alice@gmail.com", "alice@work.com"]
    assert author["commits"] == 2
    assert author["lines_added"] == 7
    assert author["lines_removed"] == 3
