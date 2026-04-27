"""Per-file commit subjects in files_by_churn (inspectable receipts)."""

from __future__ import annotations

from datetime import datetime

from almanac.ingest import Commit, FileChange
from almanac.stats import compute_bundle
from almanac.window import Window


def _w() -> Window:
    return Window(datetime(2025, 1, 1), datetime(2025, 12, 31), "2025")


def _meta() -> dict:
    return {"path": ".", "name": "r", "head_sha": "abc"}


def _c(
    sha: str,
    ts: str,
    subject: str,
    path: str = "a.py",
    parents: list[str] | None = None,
) -> Commit:
    return Commit(
        sha=sha,
        ts=ts,
        author_name="A",
        author_email="a@x",
        parents=parents or [],
        subject=subject,
        files=[FileChange(path, 1, 0)],
    )


def test_subjects_most_recent_first_capped_at_five() -> None:
    commits: list[Commit] = []
    for i in range(6):
        commits.append(
            _c(
                f"{i:04x}",
                f"2025-02-{(1 + i):02d}T12:00:00+00:00",
                f"sub-{i}",
            )
        )
    bundle = compute_bundle(commits, _w(), _meta(), classifier_strategy="rules")
    rows = [x for x in bundle["files_by_churn"] if x["path"] == "a.py"]
    assert len(rows) == 1
    subj = rows[0]["subjects"]
    assert subj == ["sub-5", "sub-4", "sub-3", "sub-2", "sub-1"]


def test_subjects_excludes_merge_commits() -> None:
    commits = [
        _c("a", "2025-02-01T12:00:00+00:00", "first"),
        Commit(
            sha="m1",
            ts="2025-02-02T12:00:00+00:00",
            author_name="A",
            author_email="a@x",
            parents=["a", "b"],
            subject="Merge branch 'x'",
            files=[FileChange("a.py", 1, 0)],
        ),
        _c("c", "2025-02-03T12:00:00+00:00", "last"),
    ]
    bundle = compute_bundle(commits, _w(), _meta(), classifier_strategy="rules")
    subj = bundle["files_by_churn"][0]["subjects"]
    assert subj == ["last", "first"]
