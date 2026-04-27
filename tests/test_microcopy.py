from __future__ import annotations

from datetime import datetime

from almanac import microcopy
from almanac.ingest import Commit, FileChange
from almanac.stats import compute_bundle
from almanac.window import Window

# --- helpers ---------------------------------------------------------------


def test_humanize_uses_thousands_separator():
    assert microcopy._humanize(1240) == "1,240"
    assert microcopy._humanize(12431) == "12,431"
    assert microcopy._humanize(0) == "0"


def test_pluralize():
    assert microcopy._pluralize("commit", 1) == "commit"
    assert microcopy._pluralize("commit", 2) == "commits"
    assert microcopy._pluralize("day", 14) == "days"
    assert microcopy._pluralize("file", 0) == "files"


def test_hour_phrase_special_cases():
    assert microcopy._hour_phrase(0) == "midnight"
    assert microcopy._hour_phrase(12) == "noon"
    assert microcopy._hour_phrase(9) == "9 AM"
    assert microcopy._hour_phrase(23) == "11 PM"
    assert microcopy._hour_phrase(13) == "1 PM"


def test_lower_first_normal():
    assert microcopy._lower_first("Initial CLI wiring") == "initial CLI wiring"
    assert microcopy._lower_first("Add things") == "add things"


def test_lower_first_skips_acronym_starts():
    # Second char is uppercase — leave the leading char alone
    assert microcopy._lower_first("iOS app launched") == "iOS app launched"
    assert microcopy._lower_first("eBPF probe added") == "eBPF probe added"
    assert microcopy._lower_first("gRPC migration") == "gRPC migration"


def test_short_path_returns_basename():
    assert microcopy._short_path("almanac/stats.py") == "stats.py"
    assert microcopy._short_path("a/b/c/d.txt") == "d.txt"
    assert microcopy._short_path("foo.py") == "foo.py"


# --- per-slot positive cases ----------------------------------------------


def _bundle_with(highlights: dict, **top_level) -> dict:
    base = {
        "window": {"label": "2025"},
        "commit_count": 0,
        "lines_added": 0,
        "lines_removed": 0,
        "highlights": highlights,
    }
    base.update(top_level)
    return base


def test_cover_intro_uses_window_label_and_first_subject():
    b = _bundle_with(
        {
            "first_commit": {
                "sha": "1",
                "ts": "x",
                "subject": "initial CLI wiring",
                "author": "a",
            }
        }
    )
    assert microcopy.cover_intro(b) == "The 2025 began with initial CLI wiring."


def test_cover_intro_strips_trailing_period():
    b = _bundle_with(
        {
            "first_commit": {
                "sha": "1",
                "ts": "x",
                "subject": "Bootstrap repo.",
                "author": "a",
            }
        }
    )
    assert microcopy.cover_intro(b) == "The 2025 began with bootstrap repo."


def test_cadence_caption_renders_pm():
    b = _bundle_with({"peak_hour": {"hour": 23, "count": 1, "share": 1.0}})
    assert microcopy.cadence_caption(b) == "Most likely to ship at 11 PM."


def test_cadence_caption_renders_midnight():
    b = _bundle_with({"peak_hour": {"hour": 0, "count": 1, "share": 1.0}})
    assert microcopy.cadence_caption(b) == "Most likely to ship at midnight."


def test_cadence_caption_renders_noon():
    b = _bundle_with({"peak_hour": {"hour": 12, "count": 1, "share": 1.0}})
    assert microcopy.cadence_caption(b) == "Most likely to ship at noon."


def test_top_files_caption_had_a_year_when_heavily_edited():
    b = _bundle_with(
        {"most_touched_file": {"path": "almanac/stats.py", "edits": 27, "lines": 1832}}
    )
    assert microcopy.top_files_caption(b) == "stats.py had a year."


def test_top_files_caption_softer_line_when_lightly_edited():
    b = _bundle_with(
        {"most_touched_file": {"path": "src/foo.py", "edits": 3, "lines": 80}}
    )
    assert microcopy.top_files_caption(b) == "foo.py got the most attention."


def test_verbs_caption_dominant_verb_share():
    b = _bundle_with({"dominant_verb": {"verb": "feat", "count": 41, "share": 0.3402}})
    assert microcopy.verbs_caption(b) == "Mostly feat work — 34% of the year."


def test_quiet_caption_uses_gap_days():
    b = _bundle_with(
        {
            "longest_quiet": {
                "days": 42,
                "start_date": "2025-12-15",
                "end_date": "2026-01-25",
            }
        }
    )
    assert microcopy.quiet_caption(b) == "42 days without a commit."


def test_comeback_caption_includes_gap_and_return():
    b = _bundle_with(
        {
            "comeback": {
                "gap_days": 42,
                "return_date": "2026-01-26",
                "return_window_commits": 9,
            }
        }
    )
    assert (
        microcopy.comeback_caption(b)
        == "A quiet spell of 42 days, then back with 9 commits in a fortnight."
    )


def test_numbers_caption_singular():
    b = _bundle_with({}, commit_count=1, lines_added=42, lines_removed=0)
    assert microcopy.numbers_caption(b) == "1 commit, 42 added, 0 removed."


def test_numbers_caption_plural_with_thousands():
    b = _bundle_with({}, commit_count=1240, lines_added=12431, lines_removed=8019)
    assert microcopy.numbers_caption(b) == "1,240 commits, 12,431 added, 8,019 removed."


def test_closer_signoff_uses_last_commit_and_streak():
    b = _bundle_with(
        {
            "last_commit": {
                "sha": "z",
                "ts": "x",
                "subject": "Ship the thing",
                "author": "a",
            },
            "longest_streak": {
                "days": 14,
                "start_date": "2025-09-01",
                "end_date": "2025-09-14",
            },
        }
    )
    assert (
        microcopy.closer_signoff(b) == "Closed on ship the thing after a 14-day streak."
    )


def test_closer_signoff_singular_streak():
    b = _bundle_with(
        {
            "last_commit": {
                "sha": "z",
                "ts": "x",
                "subject": "Ship the thing",
                "author": "a",
            },
            "longest_streak": {
                "days": 1,
                "start_date": "2025-09-01",
                "end_date": "2025-09-01",
            },
        }
    )
    assert (
        microcopy.closer_signoff(b) == "Closed on ship the thing after a 1-day streak."
    )


# --- per-slot null fallback ------------------------------------------------


def test_cover_intro_null_when_no_first_commit():
    assert microcopy.cover_intro(_bundle_with({"first_commit": None})) is None


def test_cadence_caption_null_when_no_peak_hour():
    assert microcopy.cadence_caption(_bundle_with({"peak_hour": None})) is None


def test_top_files_caption_null_when_no_top_file():
    assert (
        microcopy.top_files_caption(_bundle_with({"most_touched_file": None})) is None
    )


def test_verbs_caption_null_when_no_dominant():
    assert microcopy.verbs_caption(_bundle_with({"dominant_verb": None})) is None


def test_quiet_caption_null_when_no_quiet():
    assert microcopy.quiet_caption(_bundle_with({"longest_quiet": None})) is None


def test_comeback_caption_null_when_no_comeback():
    assert microcopy.comeback_caption(_bundle_with({"comeback": None})) is None


def test_numbers_caption_null_when_zero_commits():
    b = _bundle_with({}, commit_count=0, lines_added=0, lines_removed=0)
    assert microcopy.numbers_caption(b) is None


def test_closer_signoff_null_when_both_missing():
    b = _bundle_with({"last_commit": None, "longest_streak": None})
    assert microcopy.closer_signoff(b) is None


# --- compute() entrypoint --------------------------------------------------


def test_compute_returns_canonical_slot_set():
    b = _bundle_with(
        {
            "first_commit": None,
            "last_commit": None,
            "biggest_commit": None,
            "longest_streak": None,
            "longest_quiet": None,
            "busiest_day": None,
            "peak_hour": None,
            "most_touched_file": None,
            "dominant_verb": None,
            "comeback": None,
        }
    )
    result = microcopy.compute(b)
    assert set(result.keys()) == set(microcopy.SLOTS)
    # All slots should be None for an empty highlights set
    assert all(v is None for v in result.values())


def test_compute_values_are_strings_or_none():
    b = _bundle_with(
        {
            "first_commit": {
                "sha": "1",
                "ts": "x",
                "subject": "feat: x",
                "author": "a",
            },
            "last_commit": {"sha": "2", "ts": "x", "subject": "feat: y", "author": "a"},
            "biggest_commit": None,
            "longest_streak": {
                "days": 3,
                "start_date": "2025-09-01",
                "end_date": "2025-09-03",
            },
            "longest_quiet": None,
            "busiest_day": None,
            "peak_hour": {"hour": 14, "count": 5, "share": 0.5},
            "most_touched_file": None,
            "dominant_verb": None,
            "comeback": None,
        },
        commit_count=10,
        lines_added=100,
        lines_removed=20,
    )
    result = microcopy.compute(b)
    for v in result.values():
        assert v is None or (isinstance(v, str) and len(v) > 0)


def test_compute_is_deterministic():
    b = _bundle_with(
        {
            "first_commit": {
                "sha": "1",
                "ts": "x",
                "subject": "feat: thing",
                "author": "a",
            },
            "last_commit": {
                "sha": "2",
                "ts": "x",
                "subject": "feat: other",
                "author": "a",
            },
            "biggest_commit": None,
            "longest_streak": {
                "days": 14,
                "start_date": "2025-09-01",
                "end_date": "2025-09-14",
            },
            "longest_quiet": {
                "days": 42,
                "start_date": "2025-12-15",
                "end_date": "2026-01-25",
            },
            "busiest_day": {"date": "2025-11-04", "count": 9},
            "peak_hour": {"hour": 23, "count": 87, "share": 0.18},
            "most_touched_file": {
                "path": "almanac/stats.py",
                "edits": 27,
                "lines": 1832,
            },
            "dominant_verb": {"verb": "feat", "count": 41, "share": 0.3402},
            "comeback": {
                "gap_days": 42,
                "return_date": "2026-01-26",
                "return_window_commits": 9,
            },
        },
        commit_count=1240,
        lines_added=12431,
        lines_removed=8019,
    )
    a = microcopy.compute(b)
    c = microcopy.compute(b)
    assert a == c


# --- bundle integration ----------------------------------------------------


def _w(label: str = "2025") -> Window:
    return Window(datetime(2025, 1, 1), datetime(2026, 12, 31), label)


def _meta() -> dict:
    return {"path": ".", "name": "repo", "head_sha": "abc"}


def test_compute_bundle_attaches_microcopy():
    commits = [
        Commit(
            "1",
            "2025-06-15T14:30:00+00:00",
            "Alice",
            "a@x.com",
            [],
            "feat: ship it",
            [FileChange("a.py", 1, 0)],
        ),
    ]
    bundle = compute_bundle(commits, _w(), _meta(), classifier_strategy="rules")
    assert "microcopy" in bundle
    assert set(bundle["microcopy"].keys()) == set(microcopy.SLOTS)
    # Single commit window: cover_intro should be present, comeback null.
    assert bundle["microcopy"]["cover_intro"] is not None
    assert bundle["microcopy"]["comeback_caption"] is None


# --- golden test -----------------------------------------------------------


def test_golden_bundle():
    """Pin exact strings for a fixed sample bundle. Update intentionally."""
    bundle = _bundle_with(
        {
            "first_commit": {
                "sha": "1",
                "ts": "x",
                "subject": "Initial CLI wiring",
                "author": "a",
            },
            "last_commit": {"sha": "z", "ts": "x", "subject": "Ship it", "author": "a"},
            "biggest_commit": None,
            "longest_streak": {
                "days": 14,
                "start_date": "2025-09-01",
                "end_date": "2025-09-14",
            },
            "longest_quiet": {
                "days": 42,
                "start_date": "2025-12-15",
                "end_date": "2026-01-25",
            },
            "busiest_day": {"date": "2025-11-04", "count": 9},
            "peak_hour": {"hour": 23, "count": 87, "share": 0.18},
            "most_touched_file": {
                "path": "almanac/stats.py",
                "edits": 27,
                "lines": 1832,
            },
            "dominant_verb": {"verb": "feat", "count": 41, "share": 0.3402},
            "comeback": {
                "gap_days": 42,
                "return_date": "2026-01-26",
                "return_window_commits": 9,
            },
        },
        commit_count=1240,
        lines_added=12431,
        lines_removed=8019,
    )
    expected = {
        "cover_intro": "The 2025 began with initial CLI wiring.",
        "numbers_caption": "1,240 commits, 12,431 added, 8,019 removed.",
        "cadence_caption": "Most likely to ship at 11 PM.",
        "top_files_caption": "stats.py had a year.",
        "verbs_caption": "Mostly feat work — 34% of the year.",
        "quiet_caption": "42 days without a commit.",
        "comeback_caption": "A quiet spell of 42 days, then back with 9 commits in a fortnight.",
        "closer_signoff": "Closed on ship it after a 14-day streak.",
    }
    assert microcopy.compute(bundle) == expected
