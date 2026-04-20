from datetime import UTC, datetime

import pytest

from almanac.window import resolve_window


def local(y, m, d, H=0, M=0, S=0, us=0):
    return datetime(y, m, d, H, M, S, us)


def test_year_flag():
    w = resolve_window(year=2025, since=None, until=None, now=local(2026, 4, 18))
    assert w.since == local(2025, 1, 1)
    assert w.until == local(2025, 12, 31, 23, 59, 59, 999999)
    assert w.label == "2025"


def test_year_with_since_raises():
    with pytest.raises(Exception):
        resolve_window(
            year=2025, since="2025-06-01", until=None, now=local(2026, 4, 18)
        )


def test_year_with_until_raises():
    with pytest.raises(Exception):
        resolve_window(
            year=2025, since=None, until="2025-12-31", now=local(2026, 4, 18)
        )


def test_since_only():
    w = resolve_window(
        year=None, since="2025-06-01", until=None, now=local(2026, 4, 18)
    )
    assert w.since.date().isoformat() == "2025-06-01"
    assert w.until is not None


def test_since_until():
    w = resolve_window(
        year=None, since="2025-01-01", until="2025-12-31", now=local(2026, 4, 18)
    )
    assert w.since.date().isoformat() == "2025-01-01"
    assert w.until.date().isoformat() == "2025-12-31"


def test_default_trailing_12_months():
    now = local(2026, 4, 18)
    w = resolve_window(year=None, since=None, until=None, now=now)
    assert w.since.year == 2025
    assert w.since.month == 4
    assert w.since.day == 18
    assert w.until.year == 2026
    assert w.until.month == 4
    assert w.until.day == 18


def test_until_bare_date_includes_end_of_day():
    w = resolve_window(
        year=None, since="2026-01-01", until="2026-01-01", now=local(2026, 4, 18)
    )
    assert w.until == local(2026, 1, 1, 23, 59, 59, 999999)
    # A commit at 14:00 on the end day is still inside the window.
    commit_ts = local(2026, 1, 1, 14, 0, 0)
    assert w.since <= commit_ts <= w.until


def test_since_with_tz_offset_is_preserved():
    w = resolve_window(
        year=None,
        since="2026-01-01T00:00:00+02:00",
        until=None,
        now=local(2026, 4, 18),
    )
    assert w.since.tzinfo is not None
    assert w.since.utcoffset().total_seconds() == 2 * 3600


def test_year_covers_inclusive_end():
    w = resolve_window(year=2025, since=None, until=None, now=local(2026, 4, 18))
    inside = local(2025, 12, 31, 22, 0, 0)
    outside = local(2026, 1, 1, 0, 30, 0)
    assert w.since <= inside <= w.until
    assert not (w.since <= outside <= w.until)


def test_resolve_accepts_tz_aware_now():
    # `datetime.now(tz=UTC)` from callers shouldn't explode even though
    # the Window is naive-by-design now.
    utc_now = datetime(2026, 4, 18, tzinfo=UTC)
    w = resolve_window(year=None, since=None, until=None, now=utc_now)
    assert w.since.tzinfo is None
    assert w.until.tzinfo is None


def test_inverted_since_until_raises():
    with pytest.raises(Exception, match="cannot be later"):
        resolve_window(
            year=None,
            since="2025-12-31",
            until="2025-01-01",
            now=local(2026, 4, 18),
        )
