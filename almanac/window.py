from datetime import datetime, timedelta
from typing import NamedTuple

import click


class Window(NamedTuple):
    since: datetime
    until: datetime
    label: str


def _parse_boundary(value: str, *, end_of_day: bool) -> datetime:
    """Parse `--since` / `--until` values with these rules.

    - Bare date (``YYYY-MM-DD``) → start-of-day for ``since``,
      end-of-day for ``until``. Returned naive so it compares against
      author-local ``%aI`` timestamps.
    - ISO string with tz → preserve tz.
    - ISO string without tz → preserve naivety.
    """
    dt = datetime.fromisoformat(value)
    if len(value) == 10 and "T" not in value:
        dt = (
            dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            if end_of_day
            else dt
        )
    return dt


def resolve_window(
    year: int | None,
    since: str | None,
    until: str | None,
    now: datetime | None = None,
) -> Window:
    if now is None:
        now = datetime.now().replace(tzinfo=None)
    elif now.tzinfo is not None:
        # Accept tz-aware `now` from callers (tests) but strip the tz so
        # window bounds stay in the same convention as author-local
        # timestamps parsed from `%aI`.
        now = now.replace(tzinfo=None)

    if year is not None and (since is not None or until is not None):
        raise click.UsageError("--year cannot be combined with --since or --until")

    if year is not None:
        since_dt = datetime(year, 1, 1)
        until_dt = datetime(year, 12, 31, 23, 59, 59, 999999)
        return Window(since=since_dt, until=until_dt, label=str(year))

    if since is not None or until is not None:
        since_dt = (
            _parse_boundary(since, end_of_day=False)
            if since is not None
            else None
        )
        until_dt = _parse_boundary(until, end_of_day=True) if until is not None else None
        if since_dt is None:
            since_dt = datetime(2000, 1, 1)
            if until_dt is not None and until_dt.tzinfo is not None:
                since_dt = since_dt.replace(tzinfo=until_dt.tzinfo)
        if until_dt is None:
            until_dt = now
            if since_dt.tzinfo is not None:
                until_dt = until_dt.replace(tzinfo=since_dt.tzinfo)
        if since_dt > until_dt:
            raise click.UsageError("--since cannot be later than --until")
        label = f"{since_dt.date()}..{until_dt.date()}"
        return Window(since=since_dt, until=until_dt, label=label)

    today = datetime(now.year, now.month, now.day)
    since_dt = today - timedelta(days=365)
    until_dt = today.replace(hour=23, minute=59, second=59, microsecond=999999)
    label = f"{since_dt.date()}..{until_dt.date()}"
    return Window(since=since_dt, until=until_dt, label=label)
