import heapq
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import NamedTuple

from almanac import microcopy
from almanac.classifier import BUNDLE_VERB_KEYS, classify_batch
from almanac.ingest import Commit, coalesce_identities
from almanac.window import Window

COMEBACK_GAP_THRESHOLD = 14
COMEBACK_RETURN_WINDOW = 14
COMEBACK_MIN_COMMITS = 5


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


class _CommitFacts(NamedTuple):
    commit: Commit
    dt: datetime
    day: date
    lines_added: int
    lines_removed: int

    @property
    def delta(self) -> int:
        return self.lines_added + self.lines_removed


def _canonical_author_key(
    commit: Commit, canonical: dict[str, str] | None = None
) -> tuple[str, str]:
    email = commit.author_email.lower()
    preferred_name = (canonical or {}).get(email, commit.author_name).strip()
    if preferred_name:
        return ("name", preferred_name.casefold())
    return ("email", email)


class _StreakGap(NamedTuple):
    streak_days: int
    streak_start: date | None
    streak_end: date | None
    gap_days: int
    gap_start: date | None
    gap_end: date | None


def _compute_streak_gap(dates: list[date]) -> _StreakGap:
    if not dates:
        return _StreakGap(0, None, None, 0, None, None)
    sorted_dates = sorted(set(dates))

    max_streak = current_streak = 1
    streak_start = streak_end = sorted_dates[0]
    current_start = sorted_dates[0]
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
                streak_start = current_start
                streak_end = sorted_dates[i]
        else:
            current_streak = 1
            current_start = sorted_dates[i]

    max_gap = 0
    gap_start: date | None = None
    gap_end: date | None = None
    for i in range(1, len(sorted_dates)):
        gap = (sorted_dates[i] - sorted_dates[i - 1]).days - 1
        if gap > max_gap:
            max_gap = gap
            gap_start = sorted_dates[i - 1] + timedelta(days=1)
            gap_end = sorted_dates[i] - timedelta(days=1)

    return _StreakGap(max_streak, streak_start, streak_end, max_gap, gap_start, gap_end)


def _build_commit_facts(commits: list[Commit]) -> list[_CommitFacts]:
    facts: list[_CommitFacts] = []
    for c in commits:
        dt = _parse_ts(c.ts)
        facts.append(
            _CommitFacts(
                commit=c,
                dt=dt,
                day=dt.date(),
                lines_added=sum(f.lines_added for f in c.files),
                lines_removed=sum(f.lines_removed for f in c.files),
            )
        )
    return facts


def _commit_brief(commit: Commit) -> dict:
    return {
        "sha": commit.sha,
        "ts": commit.ts,
        "subject": commit.subject,
        "author": commit.author_name,
    }


def _first_last_commits(commits: list[Commit]) -> tuple[dict | None, dict | None]:
    if not commits:
        return None, None
    return _commit_brief(commits[0]), _commit_brief(commits[-1])


def _classify_verbs(commits: list[Commit], strategy: str) -> dict[str, int]:
    verbs: dict[str, int] = {k: 0 for k in BUNDLE_VERB_KEYS}
    for verb, _ in classify_batch([c.subject for c in commits], strategy=strategy):
        verbs[verb] += 1
    return verbs


def _cadence(facts: list[_CommitFacts]) -> tuple[list[int], list[int]]:
    by_dow = [0] * 7
    by_hour = [0] * 24
    for fact in facts:
        by_dow[fact.dt.weekday()] += 1
        by_hour[fact.dt.hour] += 1
    return by_dow, by_hour


def _line_totals_and_biggest(
    facts: list[_CommitFacts],
) -> tuple[int, int, dict | None]:
    total_added = sum(f.lines_added for f in facts)
    total_removed = sum(f.lines_removed for f in facts)
    if not facts:
        return total_added, total_removed, None

    biggest = max(facts, key=lambda f: f.delta)
    return (
        total_added,
        total_removed,
        {
            "sha": biggest.commit.sha,
            "delta": biggest.delta,
            "subject": biggest.commit.subject,
            "ts": biggest.commit.ts,
        },
    )


def _files_and_languages(commits: list[Commit]) -> tuple[list[dict], list[dict]]:
    file_stats: dict[str, dict] = defaultdict(lambda: {"edits": 0, "lines": 0})
    ext_lines: dict[str, int] = defaultdict(int)

    for c in commits:
        for f in c.files:
            churn = f.lines_added + f.lines_removed
            file_stats[f.path]["edits"] += 1
            file_stats[f.path]["lines"] += churn
            ext_lines[Path(f.path).suffix.lower()] += churn

    top_files = heapq.nlargest(
        25, file_stats.items(), key=lambda kv: (kv[1]["edits"], kv[1]["lines"])
    )
    top_paths = {p for p, _ in top_files}
    subjects_by_path: dict[str, list[str]] = {p: [] for p in top_paths}

    for c in reversed(commits):
        if c.is_merge:
            continue
        seen_in_commit: set[str] = set()
        for f in c.files:
            p = f.path
            if p not in top_paths or p in seen_in_commit:
                continue
            seen_in_commit.add(p)
            if len(subjects_by_path[p]) < 5:
                subjects_by_path[p].append(c.subject)

    files_by_churn = [
        {"path": p, **s, "subjects": subjects_by_path.get(p, [])} for p, s in top_files
    ]

    total_ext_lines = sum(ext_lines.values())
    languages = sorted(
        [
            {
                "ext": ext,
                "lines": lines,
                "share": round(lines / total_ext_lines, 4) if total_ext_lines else 0.0,
            }
            for ext, lines in ext_lines.items()
        ],
        key=lambda x: -x["lines"],
    )
    return files_by_churn, languages


def _authors(
    facts: list[_CommitFacts], canonical: dict[str, str] | None = None
) -> list[dict]:
    commits = [fact.commit for fact in facts]
    if canonical is None:
        canonical = coalesce_identities(commits)

    author_map: dict[str, dict] = {}
    for fact in facts:
        c = fact.commit
        email = c.author_email.lower()
        author_key = ":".join(_canonical_author_key(c, canonical))
        if author_key not in author_map:
            author_map[author_key] = {
                "name": canonical.get(email, c.author_name),
                "emails": set(),
                "commits": 0,
                "lines_added": 0,
                "lines_removed": 0,
                "first_ts": c.ts,
                "last_ts": c.ts,
            }
        entry = author_map[author_key]
        entry["emails"].add(email)
        entry["commits"] += 1
        entry["lines_added"] += fact.lines_added
        entry["lines_removed"] += fact.lines_removed
        if c.ts < entry["first_ts"]:
            entry["first_ts"] = c.ts
        if c.ts > entry["last_ts"]:
            entry["last_ts"] = c.ts

    authors = [
        {
            "name": v["name"],
            "emails": sorted(v["emails"]),
            "commits": v["commits"],
            "lines_added": v["lines_added"],
            "lines_removed": v["lines_removed"],
            "first_ts": v["first_ts"],
            "last_ts": v["last_ts"],
        }
        for v in author_map.values()
    ]
    authors.sort(
        key=lambda x: (
            -x["commits"],
            str(x["name"]).casefold(),
            x["emails"][0] if x["emails"] else "",
        )
    )
    return authors


def _dense_commits_per_day(facts: list[_CommitFacts], window: Window) -> list[dict]:
    per_day_counts: dict[date, int] = defaultdict(int)
    for fact in facts:
        per_day_counts[fact.day] += 1

    commits_per_day: list[dict] = []
    cur = window.since.date()
    win_until = window.until.date()
    while cur <= win_until:
        commits_per_day.append(
            {"date": cur.isoformat(), "count": per_day_counts.get(cur, 0)}
        )
        cur += timedelta(days=1)
    return commits_per_day


HIGHLIGHT_KEYS = (
    "first_commit",
    "last_commit",
    "biggest_commit",
    "longest_streak",
    "longest_quiet",
    "busiest_day",
    "peak_hour",
    "most_touched_file",
    "dominant_verb",
    "comeback",
)


def _busiest_day(commits_per_day: list[dict]) -> dict | None:
    best: dict | None = None
    best_date: date | None = None
    for entry in commits_per_day:
        count = entry["count"]
        if count == 0:
            continue
        entry_date = date.fromisoformat(entry["date"])
        if (
            best is None
            or count > best["count"]
            or (
                count == best["count"]
                and best_date is not None
                and entry_date > best_date
            )
        ):
            best = {"date": entry["date"], "count": count}
            best_date = entry_date
    return best


def _peak_hour(by_hour: list[int]) -> dict | None:
    total = sum(by_hour)
    if total == 0:
        return None
    hour = by_hour.index(max(by_hour))
    count = by_hour[hour]
    return {"hour": hour, "count": count, "share": round(count / total, 4)}


def _dominant_verb(verbs: dict[str, int]) -> dict | None:
    total = sum(verbs.values())
    best_verb: str | None = None
    best_count = 0
    for verb in BUNDLE_VERB_KEYS:
        if verb == "unclear":
            continue
        count = verbs.get(verb, 0)
        if count > best_count:
            best_count = count
            best_verb = verb
    if best_verb is None or best_count == 0:
        return None
    share = round(best_count / total, 4) if total else 0.0
    return {"verb": best_verb, "count": best_count, "share": share}


def _most_touched_file(files_by_churn: list[dict]) -> dict | None:
    if not files_by_churn:
        return None
    top = files_by_churn[0]
    return {"path": top["path"], "edits": top["edits"], "lines": top["lines"]}


def _comeback(facts: list[_CommitFacts], streak_gap: _StreakGap) -> dict | None:
    if streak_gap.gap_days < COMEBACK_GAP_THRESHOLD or streak_gap.gap_end is None:
        return None
    return_date: date | None = None
    for fact in facts:
        if fact.day > streak_gap.gap_end:
            if return_date is None or fact.day < return_date:
                return_date = fact.day
    if return_date is None:
        return None
    window_end = return_date + timedelta(days=COMEBACK_RETURN_WINDOW - 1)
    return_window_commits = sum(
        1 for fact in facts if return_date <= fact.day <= window_end
    )
    if return_window_commits < COMEBACK_MIN_COMMITS:
        return None
    return {
        "gap_days": streak_gap.gap_days,
        "return_date": return_date.isoformat(),
        "return_window_commits": return_window_commits,
    }


def _compute_highlights(
    facts: list[_CommitFacts],
    *,
    first_commit: dict | None,
    last_commit: dict | None,
    biggest_commit: dict | None,
    streak_gap: _StreakGap,
    commits_per_day: list[dict],
    by_hour: list[int],
    files_by_churn: list[dict],
    verbs: dict[str, int],
) -> dict:
    longest_streak: dict | None = None
    if streak_gap.streak_days > 0 and streak_gap.streak_start and streak_gap.streak_end:
        longest_streak = {
            "days": streak_gap.streak_days,
            "start_date": streak_gap.streak_start.isoformat(),
            "end_date": streak_gap.streak_end.isoformat(),
        }

    longest_quiet: dict | None = None
    if streak_gap.gap_days > 0 and streak_gap.gap_start and streak_gap.gap_end:
        longest_quiet = {
            "days": streak_gap.gap_days,
            "start_date": streak_gap.gap_start.isoformat(),
            "end_date": streak_gap.gap_end.isoformat(),
        }

    return {
        "first_commit": first_commit,
        "last_commit": last_commit,
        "biggest_commit": biggest_commit,
        "longest_streak": longest_streak,
        "longest_quiet": longest_quiet,
        "busiest_day": _busiest_day(commits_per_day),
        "peak_hour": _peak_hour(by_hour),
        "most_touched_file": _most_touched_file(files_by_churn),
        "dominant_verb": _dominant_verb(verbs),
        "comeback": _comeback(facts, streak_gap),
    }


def compute_bundle(
    commits: list[Commit],
    window: Window,
    repo_meta: dict,
    *,
    classifier_strategy: str = "auto",
    canonical: dict[str, str] | None = None,
) -> dict:
    commit_count = len(commits)
    merge_count = sum(1 for c in commits if c.is_merge)
    facts = _build_commit_facts(commits)

    first_commit, last_commit = _first_last_commits(commits)
    verbs = _classify_verbs(commits, classifier_strategy)
    by_dow, by_hour = _cadence(facts)
    total_added, total_removed, biggest_commit = _line_totals_and_biggest(facts)
    commit_dates = [fact.day for fact in facts]
    streak_gap = _compute_streak_gap(commit_dates)
    longest_streak = streak_gap.streak_days
    longest_gap = streak_gap.gap_days
    files_by_churn, languages = _files_and_languages(commits)
    authors = _authors(facts, canonical)
    commits_per_day = _dense_commits_per_day(facts, window)

    subjects_sample = [c.subject for c in commits[:200]]

    highlights = _compute_highlights(
        facts,
        first_commit=first_commit,
        last_commit=last_commit,
        biggest_commit=biggest_commit,
        streak_gap=streak_gap,
        commits_per_day=commits_per_day,
        by_hour=by_hour,
        files_by_churn=files_by_churn,
        verbs=verbs,
    )

    bundle = {
        "schema_version": 1,
        "repo": {
            "path": repo_meta["path"],
            "name": repo_meta["name"],
            "head_sha": repo_meta["head_sha"],
        },
        "window": {
            "since": window.since.isoformat(),
            "until": window.until.isoformat(),
            "label": window.label,
        },
        "commit_count": commit_count,
        "merge_count": merge_count,
        "first_commit": first_commit,
        "last_commit": last_commit,
        "verbs": dict(verbs),
        "by_dow": by_dow,
        "by_hour": by_hour,
        "lines_added": total_added,
        "lines_removed": total_removed,
        "biggest_commit": biggest_commit,
        "longest_streak_days": longest_streak,
        "longest_gap_days": longest_gap,
        "files_by_churn": files_by_churn,
        "languages": languages,
        "authors": authors,
        "subjects_sample": subjects_sample,
        "commits_per_day": commits_per_day,
        "highlights": highlights,
    }
    bundle["microcopy"] = microcopy.compute(bundle)
    return bundle
