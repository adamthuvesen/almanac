"""Deterministic synthetic stats bundle for demos (no git)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from almanac import microcopy
from almanac.classifier import BUNDLE_VERB_KEYS
from almanac.ingest import Commit, FileChange
from almanac.stats import (
    HIGHLIGHT_KEYS,
    _authors,
    _build_commit_facts,
    _cadence,
    _classify_verbs,
    _compute_highlights,
    _compute_streak_gap,
    _dense_commits_per_day,
    _files_and_languages,
    _first_last_commits,
    _line_totals_and_biggest,
)
from almanac.window import Window

# Fixed calendar year so output is stable across runs and timezones in CI.
DEMO_WINDOW = Window(
    since=datetime(2024, 1, 1, 0, 0, 0),
    until=datetime(2024, 12, 31, 23, 59, 59, 999999),
    label="2024",
)

# Hand-tuned repo identity (proposal: "acme/platform")
DEMO_REPO_META = {
    "path": "/demo/acme/platform",
    "name": "platform",
    "head_sha": "d0c0cafed00d1abefacedeadbeef12345678abc",
}

_DEMO_AUTHORS: tuple[tuple[str, str], ...] = (
    ("Avery Acme", "demo-author-0@example.invalid"),
    ("Blake Acme", "demo-author-1@example.invalid"),
    ("Casey Acme", "demo-author-2@example.invalid"),
    ("Drew Acme", "demo-author-3@example.invalid"),
    ("Erin Acme", "demo-author-4@example.invalid"),
)

_TOP_CHURN_PATH = "src/core/service/api_handler.py"
_LANG_PATHS: tuple[str, ...] = (
    "app/main.py",
    "lib/index.ts",
    "pkg/README.md",
    "Makefile",
    "config/ci.yml",
)


def _dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _build_synthetic_commits() -> list[Commit]:
    """Assemble a deterministic, chronologically ordered commit stream (no random)."""
    out: list[Commit] = []
    n = 0

    def next_sha() -> str:
        nonlocal n
        s = f"{n:04x}a7e2"
        n += 1
        return s

    def add(
        d: date,
        hour: int,
        minute: int,
        subject: str,
        files: list[FileChange],
        author_i: int,
        parents: list[str] | None = None,
    ) -> None:
        a = _DEMO_AUTHORS[author_i % len(_DEMO_AUTHORS)]
        name, email = a
        ts = datetime.combine(d, time(hour, minute, 0)).isoformat()
        out.append(
            Commit(
                sha=next_sha(),
                ts=ts,
                author_name=name,
                author_email=email,
                parents=parents if parents is not None else [f"p{n}"],
                subject=subject,
                files=files,
            )
        )

    def tiny_feat(d: date, h: int, m: int, subj: str, author_i: int) -> None:
        add(
            d,
            h,
            m,
            subj,
            [FileChange(_TOP_CHURN_PATH, 2, 1)],
            author_i,
        )

    def merge_commit(d: date) -> None:
        add(
            d,
            16,
            0,
            "chore: sync release branch",
            [FileChange("ops/release.sh", 1, 1)],
            3,
            parents=["p0", "p1"],
        )

    # --- 14-day streak (consecutive days), all at 16:00
    for i in range(14):
        tiny_feat(
            date(2024, 1, 1) + timedelta(days=i), 16, 0, f"feat: streak day {i}", i % 5
        )

    # Biggest line delta: single large commit
    add(
        date(2024, 1, 16),
        16,
        15,
        "feat: ship v2 data plane",
        [FileChange("src/legacy/migrate.py", 2400, 0)],
        1,
    )

    # --- Quiet stretch: last commit before gap, then 22+ quiet days, then a burst (comeback)
    # Jan 20 → Feb 12 is 23 days apart → 22 quiet days between (meets >= 21 and comeback threshold)
    tiny_feat(date(2024, 1, 20), 16, 0, "fix: last touch before hibernation", 0)
    for j in range(6):
        tiny_feat(
            date(2024, 2, 12) + timedelta(days=j // 2),
            16,
            j * 3 % 20,
            f"feat: return sprint {j}",
            j % 5,
        )

    # Merges after the comeback (avoid any commits in the Jan 20 – Feb 11 quiet window)
    for mday in (20, 27):
        merge_commit(date(2024, 2, mday))

    # --- Bulk body: start after the gap/comeback so longest_quiet stays ≥21 days
    d0 = date(2024, 3, 1)
    d1 = date(2024, 12, 31)
    day = d0
    cidx = 0
    while day <= d1 and len(out) < 5000:
        wd = day.weekday()
        if wd == 4:  # Friday: heavy at 16:00 (keeps Friday busiest and hour 16 peak)
            for k in range(18):
                subj = f"feat: friday focus {cidx} ({k})"
                tiny_feat(day, 16, k % 25, subj, cidx % 5)
                cidx += 1
        elif wd in (0, 1, 2, 3):  # Mon–Thu: lighter at 16:00
            for _ in range(2):
                p = cidx % len(_LANG_PATHS)
                add(
                    day,
                    16,
                    (cidx * 2) % 20,
                    f"chore: touch {_LANG_PATHS[p]}",
                    [FileChange(_LANG_PATHS[p], 3, 2)],
                    cidx % 5,
                )
                cidx += 1
        else:  # Sat / Sun: light, off-peak hours
            if cidx % 2 == 0:
                p = cidx % len(_LANG_PATHS)
                add(
                    day,
                    11,
                    20,
                    f"docs: weekend note {cidx}",
                    [FileChange(_LANG_PATHS[p], 1, 0)],
                    cidx % 5,
                )
                cidx += 1
        day += timedelta(days=1)

    out.sort(key=lambda c: _dt(c.ts))
    return out


def _validate_tuned_highlights(bundle: dict) -> None:
    h = bundle["highlights"]
    ph = h.get("peak_hour")
    assert ph is not None and ph.get("hour") == 16
    bd = h.get("busiest_day")
    assert bd is not None
    d = date.fromisoformat(bd["date"])
    assert d.weekday() == 4  # Friday
    ls = h.get("longest_streak")
    assert ls is not None and ls.get("days", 0) >= 14
    lq = h.get("longest_quiet")
    assert lq is not None and lq.get("days", 0) >= 21
    assert h.get("comeback") is not None
    assert h.get("dominant_verb") is not None


def _assert_bundle_schema(bundle: dict) -> None:
    assert bundle["schema_version"] == 1
    for k in BUNDLE_VERB_KEYS:
        assert k in bundle["verbs"]
        assert isinstance(bundle["verbs"][k], int)
    for k in HIGHLIGHT_KEYS:
        assert k in bundle["highlights"]
    for slot in microcopy.SLOTS:
        assert slot in bundle["microcopy"]


def make_demo_bundle() -> dict:
    """Return a fully populated, deterministic stats bundle (schema version 1)."""
    commits = _build_synthetic_commits()
    window = DEMO_WINDOW
    facts = _build_commit_facts(commits)
    commit_count = len(commits)
    merge_count = sum(1 for c in commits if c.is_merge)
    first_commit, last_commit = _first_last_commits(commits)
    verbs = _classify_verbs(commits, "rules")
    by_dow, by_hour = _cadence(facts)
    total_added, total_removed, biggest_commit = _line_totals_and_biggest(facts)
    commit_dates = [f.day for f in facts]
    streak_gap = _compute_streak_gap(commit_dates)
    files_by_churn, languages = _files_and_languages(commits)
    authors = _authors(facts, canonical=None)
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

    bundle: dict = {
        "schema_version": 1,
        "repo": {
            "path": DEMO_REPO_META["path"],
            "name": DEMO_REPO_META["name"],
            "head_sha": DEMO_REPO_META["head_sha"],
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
        "longest_streak_days": streak_gap.streak_days,
        "longest_gap_days": streak_gap.gap_days,
        "files_by_churn": files_by_churn,
        "languages": languages,
        "authors": authors,
        "subjects_sample": subjects_sample,
        "commits_per_day": commits_per_day,
        "highlights": highlights,
    }
    bundle["microcopy"] = microcopy.compute(bundle)

    _assert_bundle_schema(bundle)
    _validate_tuned_highlights(bundle)
    assert 500 <= bundle["commit_count"] <= 5000
    assert len(bundle["authors"]) >= 3
    return bundle
