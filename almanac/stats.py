import heapq
import os
from collections import defaultdict
from datetime import date, datetime

from almanac.classifier import BUNDLE_VERB_KEYS, classify_batch
from almanac.ingest import Commit, coalesce_identities
from almanac.window import Window


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _commit_date(ts: str) -> date:
    return _parse_ts(ts).date()


def _canonical_author_key(
    commit: Commit, canonical: dict[str, str] | None = None
) -> tuple[str, str]:
    email = commit.author_email.lower()
    preferred_name = (canonical or {}).get(email, commit.author_name).strip()
    if preferred_name:
        return ("name", preferred_name.casefold())
    return ("email", email)


def _compute_streak_gap(dates: list[date]) -> tuple[int, int]:
    if not dates:
        return 0, 0
    sorted_dates = sorted(set(dates))

    max_streak = current_streak = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1

    max_gap = 0
    for i in range(1, len(sorted_dates)):
        gap = (sorted_dates[i] - sorted_dates[i - 1]).days - 1
        max_gap = max(max_gap, gap)

    return max_streak, max_gap


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

    first_commit = None
    last_commit = None
    if commits:
        first_c = commits[0]
        first_commit = {
            "sha": first_c.sha,
            "ts": first_c.ts,
            "subject": first_c.subject,
            "author": first_c.author_name,
        }
        last_c = commits[-1]
        last_commit = {
            "sha": last_c.sha,
            "ts": last_c.ts,
            "subject": last_c.subject,
            "author": last_c.author_name,
        }

    # Verb classification — batch all subjects in one call
    verbs: dict[str, int] = {k: 0 for k in BUNDLE_VERB_KEYS}
    for verb, _ in classify_batch([c.subject for c in commits], strategy=classifier_strategy):
        verbs[verb] += 1

    # by_dow and by_hour using author-local time
    by_dow = [0] * 7
    by_hour = [0] * 24
    for c in commits:
        dt = _parse_ts(c.ts)
        by_dow[dt.weekday()] += 1
        by_hour[dt.hour] += 1

    # Lines added/removed and biggest commit
    total_added = 0
    total_removed = 0
    biggest_commit = None
    biggest_delta = -1

    for c in commits:
        c_added = sum(f.lines_added for f in c.files)
        c_removed = sum(f.lines_removed for f in c.files)
        total_added += c_added
        total_removed += c_removed
        delta = c_added + c_removed
        if delta > biggest_delta:
            biggest_delta = delta
            biggest_commit = {
                "sha": c.sha,
                "delta": delta,
                "subject": c.subject,
                "ts": c.ts,
            }

    # Streak and gap
    commit_dates = [_commit_date(c.ts) for c in commits]
    longest_streak, longest_gap = _compute_streak_gap(commit_dates)

    # files_by_churn
    file_stats: dict[str, dict] = defaultdict(lambda: {"edits": 0, "lines": 0})
    for c in commits:
        for f in c.files:
            file_stats[f.path]["edits"] += 1
            file_stats[f.path]["lines"] += f.lines_added + f.lines_removed

    top_files = heapq.nlargest(
        25, file_stats.items(), key=lambda kv: (kv[1]["edits"], kv[1]["lines"])
    )
    files_by_churn = [{"path": p, **s} for p, s in top_files]

    # languages
    ext_lines: dict[str, int] = defaultdict(int)
    for c in commits:
        for f in c.files:
            ext = os.path.splitext(f.path)[1].lower()
            net = max(0, f.lines_added - f.lines_removed)
            ext_lines[ext] += net

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

    # authors
    if canonical is None:
        canonical = coalesce_identities(commits)
    author_map: dict[str, dict] = {}
    for c in commits:
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
        entry["lines_added"] += sum(f.lines_added for f in c.files)
        entry["lines_removed"] += sum(f.lines_removed for f in c.files)
        if c.ts < entry["first_ts"]:
            entry["first_ts"] = c.ts
        if c.ts > entry["last_ts"]:
            entry["last_ts"] = c.ts

    authors = sorted(
        [
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
        ],
        key=lambda x: -x["commits"],
    )

    # subjects_sample: first 200 chronologically (iter_commits sorts by ts).
    subjects_sample = [c.subject for c in commits[:200]]

    # commits_per_day: dense series across the window, including zero days,
    # so the HTML calendar heatmap can render every cell.
    per_day_counts: dict[date, int] = defaultdict(int)
    for c in commits:
        per_day_counts[_commit_date(c.ts)] += 1
    commits_per_day: list[dict] = []
    win_since = window.since.date()
    win_until = window.until.date()
    if win_since <= win_until:
        cur = win_since
        while cur <= win_until:
            commits_per_day.append(
                {"date": cur.isoformat(), "count": per_day_counts.get(cur, 0)}
            )
            cur = date.fromordinal(cur.toordinal() + 1)

    return {
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
    }
