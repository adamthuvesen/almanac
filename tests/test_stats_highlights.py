from __future__ import annotations

import json
from datetime import datetime, timedelta

from almanac.ingest import Commit, FileChange
from almanac.stats import (
    HIGHLIGHT_KEYS,
    _busiest_day,
    _comeback,
    _CommitFacts,
    _compute_streak_gap,
    _dominant_verb,
    _most_touched_file,
    _peak_hour,
    compute_bundle,
)
from almanac.window import Window


def _w(label: str = "test") -> Window:
    return Window(datetime(2025, 1, 1), datetime(2026, 12, 31), label)


def _meta() -> dict:
    return {"path": ".", "name": "repo", "head_sha": "abc123"}


def _commit(
    sha: str,
    ts: str,
    subject: str = "feat: thing",
    files: list[FileChange] | None = None,
    name: str = "Alice",
    email: str = "alice@example.com",
) -> Commit:
    return Commit(
        sha=sha,
        ts=ts,
        author_name=name,
        author_email=email,
        parents=[],
        subject=subject,
        files=files or [FileChange("a.py", 1, 0)],
    )


def _facts(commits: list[Commit]) -> list[_CommitFacts]:
    out = []
    for c in commits:
        dt = datetime.fromisoformat(c.ts)
        out.append(
            _CommitFacts(
                commit=c,
                dt=dt,
                day=dt.date(),
                lines_added=sum(f.lines_added for f in c.files),
                lines_removed=sum(f.lines_removed for f in c.files),
            )
        )
    return out


# --- _compute_streak_gap with bounding dates -------------------------------


def test_streak_gap_empty_dates():
    sg = _compute_streak_gap([])
    assert sg.streak_days == 0
    assert sg.gap_days == 0
    assert sg.streak_start is None and sg.streak_end is None
    assert sg.gap_start is None and sg.gap_end is None


def test_streak_gap_single_date():
    d = datetime(2025, 9, 1).date()
    sg = _compute_streak_gap([d])
    assert sg.streak_days == 1
    assert sg.streak_start == d == sg.streak_end
    assert sg.gap_days == 0


def test_streak_gap_14_day_streak():
    base = datetime(2025, 9, 1).date()
    dates = [base + timedelta(days=i) for i in range(14)]
    sg = _compute_streak_gap(dates)
    assert sg.streak_days == 14
    assert sg.streak_start == base
    assert sg.streak_end == base + timedelta(days=13)


def test_streak_gap_42_day_gap_bounding_dates():
    last_before = datetime(2025, 12, 14).date()
    first_after = datetime(2026, 1, 26).date()
    dates = [last_before, first_after]
    sg = _compute_streak_gap(dates)
    assert sg.gap_days == 42
    assert sg.gap_start == datetime(2025, 12, 15).date()
    assert sg.gap_end == datetime(2026, 1, 25).date()


def test_streak_gap_tie_picks_earliest_streak():
    # Two 3-day streaks; earliest should win
    base = datetime(2025, 6, 1).date()
    dates = [base + timedelta(days=i) for i in range(3)] + [
        base + timedelta(days=10 + i) for i in range(3)
    ]
    sg = _compute_streak_gap(dates)
    assert sg.streak_days == 3
    assert sg.streak_start == base
    assert sg.streak_end == base + timedelta(days=2)


# --- argmax helpers --------------------------------------------------------


def test_busiest_day_picks_max_count():
    cpd = [
        {"date": "2025-11-03", "count": 4},
        {"date": "2025-11-04", "count": 9},
        {"date": "2025-11-05", "count": 2},
    ]
    assert _busiest_day(cpd) == {"date": "2025-11-04", "count": 9}


def test_busiest_day_tie_broken_by_latest_date():
    cpd = [
        {"date": "2025-06-10", "count": 5},
        {"date": "2025-08-20", "count": 5},
        {"date": "2025-04-01", "count": 4},
    ]
    assert _busiest_day(cpd) == {"date": "2025-08-20", "count": 5}


def test_busiest_day_empty_returns_none():
    assert _busiest_day([{"date": "2025-01-01", "count": 0}]) is None
    assert _busiest_day([]) is None


def test_peak_hour_argmax_with_share():
    by_hour = [0] * 24
    by_hour[23] = 87
    by_hour[10] = 50
    total = 137
    result = _peak_hour(by_hour)
    assert result == {"hour": 23, "count": 87, "share": round(87 / total, 4)}


def test_peak_hour_tie_picks_smallest():
    by_hour = [0] * 24
    by_hour[9] = 12
    by_hour[14] = 12
    result = _peak_hour(by_hour)
    assert result is not None
    assert result["hour"] == 9


def test_peak_hour_empty_returns_none():
    assert _peak_hour([0] * 24) is None


def test_dominant_verb_excludes_unclear():
    verbs = {
        "feat": 41,
        "fix": 18,
        "chore": 11,
        "docs": 0,
        "refactor": 0,
        "test": 0,
        "style": 0,
        "perf": 0,
        "build": 0,
        "ci": 0,
        "revert": 0,
        "unclear": 50,
    }
    result = _dominant_verb(verbs)
    assert result is not None
    assert result["verb"] == "feat"
    assert result["count"] == 41
    # share denominator includes unclear (total = 120)
    assert result["share"] == round(41 / 120, 4)


def test_dominant_verb_unclear_only_returns_none():
    verbs = {
        k: 0
        for k in (
            "feat",
            "fix",
            "chore",
            "docs",
            "refactor",
            "test",
            "style",
            "perf",
            "build",
            "ci",
            "revert",
        )
    }
    verbs["unclear"] = 100
    assert _dominant_verb(verbs) is None


def test_dominant_verb_all_zero_returns_none():
    verbs = {
        k: 0
        for k in (
            "feat",
            "fix",
            "chore",
            "docs",
            "refactor",
            "test",
            "style",
            "perf",
            "build",
            "ci",
            "revert",
            "unclear",
        )
    }
    assert _dominant_verb(verbs) is None


def test_most_touched_file_returns_top():
    files = [
        {"path": "almanac/stats.py", "edits": 27, "lines": 1832},
        {"path": "other.py", "edits": 5, "lines": 100},
    ]
    assert _most_touched_file(files) == {
        "path": "almanac/stats.py",
        "edits": 27,
        "lines": 1832,
    }


def test_most_touched_file_empty_returns_none():
    assert _most_touched_file([]) is None


# --- comeback detector -----------------------------------------------------


def test_comeback_positive():
    # 42-day gap ending 2026-01-25; return on 2026-01-26 with 9 commits in 14d
    return_start = datetime(2026, 1, 26)
    facts = _facts(
        [_commit("a", "2025-12-14T12:00:00+00:00")]
        + [
            _commit(
                f"r{i}",
                (return_start + timedelta(days=i)).isoformat() + "+00:00",
            )
            for i in range(9)
        ]
    )
    sg = _compute_streak_gap([f.day for f in facts])
    cb = _comeback(facts, sg)
    assert cb == {
        "gap_days": 42,
        "return_date": "2026-01-26",
        "return_window_commits": 9,
    }


def test_comeback_short_gap_returns_none():
    facts = _facts(
        [_commit("a", "2026-01-01T10:00:00+00:00")]
        + [_commit(f"r{i}", f"2026-01-{10 + i}T10:00:00+00:00") for i in range(6)]
    )
    sg = _compute_streak_gap([f.day for f in facts])
    assert sg.gap_days == 8  # < 14
    assert _comeback(facts, sg) is None


def test_comeback_long_gap_sparse_return_returns_none():
    return_start = datetime(2026, 1, 26)
    facts = _facts(
        [_commit("a", "2025-12-14T12:00:00+00:00")]
        + [
            _commit(
                f"r{i}",
                (return_start + timedelta(days=i)).isoformat() + "+00:00",
            )
            for i in range(3)  # only 3, < 5
        ]
    )
    sg = _compute_streak_gap([f.day for f in facts])
    cb = _comeback(facts, sg)
    assert cb is None


def test_comeback_single_commit_returns_none():
    facts = _facts([_commit("a", "2025-12-14T12:00:00+00:00")])
    sg = _compute_streak_gap([f.day for f in facts])
    assert _comeback(facts, sg) is None


# --- bundle integration ----------------------------------------------------


def test_highlights_block_has_canonical_keys():
    commits = [_commit("1", "2025-06-01T10:00:00+00:00")]
    bundle = compute_bundle(commits, _w("2025"), _meta(), classifier_strategy="rules")
    assert "highlights" in bundle
    assert set(bundle["highlights"].keys()) == set(HIGHLIGHT_KEYS)


def test_highlights_round_trip_through_json():
    commits = [
        _commit(f"c{i}", f"2025-06-{1 + i:02d}T10:00:00+00:00") for i in range(5)
    ]
    bundle = compute_bundle(commits, _w("2025"), _meta(), classifier_strategy="rules")
    parsed = json.loads(json.dumps(bundle["highlights"]))
    assert parsed == bundle["highlights"]


def test_highlights_empty_window_emits_nulls():
    bundle = compute_bundle([], _w("empty"), _meta(), classifier_strategy="rules")
    h = bundle["highlights"]
    assert h["first_commit"] is None
    assert h["last_commit"] is None
    assert h["biggest_commit"] is None
    assert h["longest_streak"] is None
    assert h["longest_quiet"] is None
    assert h["busiest_day"] is None
    assert h["peak_hour"] is None
    assert h["most_touched_file"] is None
    assert h["dominant_verb"] is None
    assert h["comeback"] is None


def test_highlights_single_commit():
    commits = [_commit("1", "2025-06-15T14:30:00+00:00", "feat: ship it")]
    bundle = compute_bundle(commits, _w("2025"), _meta(), classifier_strategy="rules")
    h = bundle["highlights"]
    assert h["first_commit"] == h["last_commit"]
    assert h["longest_streak"] == {
        "days": 1,
        "start_date": "2025-06-15",
        "end_date": "2025-06-15",
    }
    assert h["longest_quiet"] is None
    assert h["busiest_day"] == {"date": "2025-06-15", "count": 1}
    assert h["peak_hour"]["hour"] == 14
    assert h["dominant_verb"]["verb"] == "feat"
    assert h["comeback"] is None


def test_highlights_streak_with_bounding_dates():
    base = datetime(2025, 9, 1)
    commits = [
        _commit(f"c{i}", (base + timedelta(days=i)).isoformat() + "+00:00")
        for i in range(14)
    ]
    bundle = compute_bundle(commits, _w("2025"), _meta(), classifier_strategy="rules")
    assert bundle["highlights"]["longest_streak"] == {
        "days": 14,
        "start_date": "2025-09-01",
        "end_date": "2025-09-14",
    }
    assert (
        bundle["highlights"]["longest_streak"]["days"] == bundle["longest_streak_days"]
    )


def test_highlights_quiet_period_with_bounding_dates():
    commits = [
        _commit("a", "2025-12-14T12:00:00+00:00"),
        _commit("b", "2026-01-26T12:00:00+00:00"),
    ]
    bundle = compute_bundle(
        commits, _w("2025-26"), _meta(), classifier_strategy="rules"
    )
    assert bundle["highlights"]["longest_quiet"] == {
        "days": 42,
        "start_date": "2025-12-15",
        "end_date": "2026-01-25",
    }


def test_existing_top_level_fields_preserved():
    commits = [
        _commit("1", "2025-06-01T10:00:00+00:00"),
        _commit("2", "2025-06-02T10:00:00+00:00"),
    ]
    bundle = compute_bundle(commits, _w("2025"), _meta(), classifier_strategy="rules")
    # Sanity that nothing was removed or re-shaped.
    assert bundle["schema_version"] == 1
    assert "longest_streak_days" in bundle
    assert "longest_gap_days" in bundle
    assert "biggest_commit" in bundle
    assert "first_commit" in bundle
    assert "last_commit" in bundle
    assert bundle["highlights"]["biggest_commit"] == bundle["biggest_commit"]
