"""Deterministic, data-backed micro-copy for the Almanac report.

Every slot is a pure function of the StatsBundle. No model calls, no
randomness, no clock reads. If a slot's underlying signal is absent,
the slot returns ``None`` — never a placeholder string.
"""

from __future__ import annotations

from pathlib import Path

SLOTS = (
    "cover_intro",
    "numbers_caption",
    "cadence_caption",
    "top_files_caption",
    "verbs_caption",
    "quiet_caption",
    "comeback_caption",
    "closer_signoff",
)


def _humanize(n: int) -> str:
    return f"{n:,}"


_PLURAL_OVERRIDES: dict[str, str] = {}


def _pluralize(word: str, n: int) -> str:
    if n == 1:
        return word
    return _PLURAL_OVERRIDES.get(word, word + "s")


def _hour_phrase(h: int) -> str:
    if h == 0:
        return "midnight"
    if h == 12:
        return "noon"
    if h < 12:
        return f"{h} AM"
    return f"{h - 12} PM"


def _lower_first(s: str) -> str:
    if not s:
        return s
    if len(s) >= 2 and s[1].isupper():
        return s
    return s[0].lower() + s[1:]


def _short_path(path: str) -> str:
    return Path(path).name


def cover_intro(bundle: dict) -> str | None:
    first = bundle.get("highlights", {}).get("first_commit")
    if first is None:
        return None
    label = bundle.get("window", {}).get("label", "")
    subject = first["subject"].strip().rstrip(".")
    return f"The {label} began with {_lower_first(subject)}."


def numbers_caption(bundle: dict) -> str | None:
    n = bundle.get("commit_count", 0)
    if n == 0:
        return None
    added = bundle.get("lines_added", 0)
    removed = bundle.get("lines_removed", 0)
    return (
        f"{_humanize(n)} {_pluralize('commit', n)}, "
        f"{_humanize(added)} added, {_humanize(removed)} removed."
    )


def cadence_caption(bundle: dict) -> str | None:
    peak = bundle.get("highlights", {}).get("peak_hour")
    if peak is None:
        return None
    return f"Most likely to ship at {_hour_phrase(peak['hour'])}."


def top_files_caption(bundle: dict) -> str | None:
    top = bundle.get("highlights", {}).get("most_touched_file")
    if top is None:
        return None
    name = _short_path(top["path"])
    if top["edits"] >= 10:
        return f"{name} had a year."
    return f"{name} got the most attention."


def verbs_caption(bundle: dict) -> str | None:
    dom = bundle.get("highlights", {}).get("dominant_verb")
    if dom is None:
        return None
    pct = round(dom["share"] * 100)
    return f"Mostly {dom['verb']} work — {pct}% of the year."


def quiet_caption(bundle: dict) -> str | None:
    q = bundle.get("highlights", {}).get("longest_quiet")
    if q is None:
        return None
    return f"{q['days']} days without a commit."


def comeback_caption(bundle: dict) -> str | None:
    cb = bundle.get("highlights", {}).get("comeback")
    if cb is None:
        return None
    return (
        f"A quiet spell of {cb['gap_days']} days, then back with "
        f"{cb['return_window_commits']} commits in a fortnight."
    )


def closer_signoff(bundle: dict) -> str | None:
    last = bundle.get("highlights", {}).get("last_commit")
    streak = bundle.get("highlights", {}).get("longest_streak")
    if last is None and streak is None:
        return None
    if last is not None and streak is not None:
        subject = last["subject"].strip().rstrip(".")
        return f"Closed on {_lower_first(subject)} after a {streak['days']}-day streak."
    if last is not None:
        subject = last["subject"].strip().rstrip(".")
        return f"Closed on {_lower_first(subject)}."
    return f"Capped by a {streak['days']}-day streak."


_DISPATCH = {
    "cover_intro": cover_intro,
    "numbers_caption": numbers_caption,
    "cadence_caption": cadence_caption,
    "top_files_caption": top_files_caption,
    "verbs_caption": verbs_caption,
    "quiet_caption": quiet_caption,
    "comeback_caption": comeback_caption,
    "closer_signoff": closer_signoff,
}


def compute(bundle: dict) -> dict[str, str | None]:
    return {slot: _DISPATCH[slot](bundle) for slot in SLOTS}
