import pytest

from almanac.slides import SLIDES


@pytest.fixture
def bundle():
    return {
        "repo": {"name": "demo-repo", "head_sha": "abc"},
        "window": {"label": "2025", "since": "2025-01-01", "until": "2025-12-31"},
        "commit_count": 120,
        "merge_count": 5,
        "lines_added": 3400,
        "lines_removed": 1100,
        "longest_streak_days": 9,
        "longest_gap_days": 4,
        "biggest_commit": {"delta": 420, "subject": "big", "sha": "x", "ts": "t"},
        "by_dow": [12, 20, 24, 18, 22, 14, 10],
        "by_hour": [i for i in range(24)],
        "files_by_churn": [
            {"path": f"src/file_{i}.py", "edits": 30 - i, "lines": 100 - i}
            for i in range(25)
        ],
        "languages": [
            {"ext": ".py", "lines": 3000, "share": 0.75},
            {"ext": ".md", "lines": 800, "share": 0.20},
            {"ext": ".yaml", "lines": 200, "share": 0.05},
        ],
        "verbs": {
            "feat": 40,
            "fix": 30,
            "chore": 20,
            "docs": 10,
            "refactor": 5,
            "test": 5,
            "style": 0,
            "perf": 0,
            "build": 0,
            "ci": 0,
            "revert": 0,
            "unclear": 10,
        },
        "authors": [
            {
                "name": f"author-{i}",
                "commits": 15 - i,
                "lines_added": 500 - i * 20,
                "lines_removed": 200 - i * 10,
            }
            for i in range(12)
        ],
    }


@pytest.mark.parametrize("slide", SLIDES, ids=[s.name for s in SLIDES])
def test_slide_renders_non_empty_at_80x24(slide, bundle):
    out = slide(bundle, 80, 24)
    assert isinstance(out, str)
    assert out.strip() != ""


@pytest.mark.parametrize("slide", SLIDES, ids=[s.name for s in SLIDES])
def test_slide_renders_at_narrow_min(slide, bundle):
    out = slide(bundle, 80, 24)
    assert out


@pytest.mark.parametrize("slide", SLIDES, ids=[s.name for s in SLIDES])
def test_slide_renders_at_wide(slide, bundle):
    out = slide(bundle, 220, 50)
    assert out


def test_authors_slide_caps_at_10(bundle):
    from almanac.slides.authors import slide as authors_slide

    out = authors_slide(bundle, 80, 24)
    # 12 authors in fixture: 10 shown → "…and 2 more" footer
    assert "…and 2 more" in out


def test_authors_slide_strips_ansi_from_name(bundle):
    from almanac.slides.authors import slide as authors_slide

    hostile_bundle = dict(bundle)
    hostile_bundle["authors"] = [
        {
            "name": "\x1b[2J\x1b[Hevil",
            "commits": 10,
            "lines_added": 1,
            "lines_removed": 0,
        }
    ]
    out = authors_slide(hostile_bundle, 80, 24)
    assert "\x1b[2J" not in out
    assert "\x1b[H" not in out
    # The sanitized label should still be visible.
    assert "evil" in out


def test_top_files_slide_strips_osc_from_path(bundle):
    from almanac.slides.top_files import slide as top_files_slide

    hostile_bundle = dict(bundle)
    hostile_bundle["files_by_churn"] = [
        {"path": "src/\x1b]0;title\x07ok.py", "edits": 5, "lines": 10}
    ]
    out = top_files_slide(hostile_bundle, 80, 24)
    assert "\x1b]" not in out
    assert "\x07" not in out
    assert "ok.py" in out


def test_languages_slide_strips_ansi_from_ext(bundle):
    from almanac.slides.languages import slide as languages_slide

    hostile_bundle = dict(bundle)
    hostile_bundle["languages"] = [
        {"ext": ".\x1b[2Jpy", "lines": 100, "share": 1.0},
    ]
    out = languages_slide(hostile_bundle, 80, 24)
    assert "\x1b[2J" not in out


def test_languages_sum_to_100_pct(bundle):
    from almanac.slides.languages import slide as languages_slide

    out = languages_slide(bundle, 80, 24)
    # Each language row has "XX.X%" — extract and sum
    import re

    pcts = [float(m.group(1)) for m in re.finditer(r"(\d+\.\d)%", out)]
    assert pcts
    assert 99.0 <= sum(pcts) <= 101.0


# --- microcopy integration -------------------------------------------------


def _strip_ansi(s: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", s)


def test_cover_slide_renders_cover_intro(bundle):
    from almanac.slides.cover import slide as cover_slide

    bundle = dict(bundle)
    bundle["microcopy"] = {"cover_intro": "The 2025 began with initial CLI wiring."}
    out = cover_slide(bundle, 80, 24)
    assert "The 2025 began with initial CLI wiring." in _strip_ansi(out)


def test_cover_slide_omits_caption_when_slot_null(bundle):
    from almanac.slides.cover import slide as cover_slide

    out_without = cover_slide(dict(bundle), 80, 24)
    bundle_with_null = dict(bundle)
    bundle_with_null["microcopy"] = {"cover_intro": None}
    out_null = cover_slide(bundle_with_null, 80, 24)
    assert out_without == out_null


def test_cadence_slide_renders_cadence_caption(bundle):
    from almanac.slides.cadence import slide as cadence_slide

    bundle = dict(bundle)
    bundle["microcopy"] = {
        "cadence_caption": "Most likely to ship at 11 PM.",
        "comeback_caption": None,
        "quiet_caption": None,
    }
    out = cadence_slide(bundle, 100, 30)
    assert "Most likely to ship at 11 PM." in _strip_ansi(out)


def test_cadence_slide_renders_quiet_when_no_comeback(bundle):
    from almanac.slides.cadence import slide as cadence_slide

    bundle = dict(bundle)
    bundle["microcopy"] = {
        "cadence_caption": "Most likely to ship at 11 PM.",
        "comeback_caption": None,
        "quiet_caption": "42 days without a commit.",
    }
    out = cadence_slide(bundle, 100, 30)
    assert "42 days without a commit." in _strip_ansi(out)


def test_top_files_slide_renders_caption(bundle):
    from almanac.slides.top_files import slide as top_files_slide

    bundle = dict(bundle)
    bundle["microcopy"] = {"top_files_caption": "stats.py had a year."}
    out = top_files_slide(bundle, 100, 30)
    assert "stats.py had a year." in _strip_ansi(out)


def test_verbs_slide_renders_caption(bundle):
    from almanac.slides.verbs import slide as verbs_slide

    bundle = dict(bundle)
    bundle["microcopy"] = {"verbs_caption": "Mostly feat work — 40% of the year."}
    out = verbs_slide(bundle, 100, 30)
    assert "Mostly feat work — 40% of the year." in _strip_ansi(out)


def test_authors_slide_renders_closer_signoff(bundle):
    from almanac.slides.authors import slide as authors_slide

    bundle = dict(bundle)
    bundle["microcopy"] = {"closer_signoff": "Closed on ship it after a 14-day streak."}
    out = authors_slide(bundle, 120, 30)
    assert "Closed on ship it after a 14-day streak." in _strip_ansi(out)


def test_microcopy_strips_esc_bytes_in_caption(bundle):
    from almanac.slides.cover import slide as cover_slide

    bundle = dict(bundle)
    bundle["microcopy"] = {"cover_intro": "hostile \x1b[31mred\x1b[0m text"}
    out = cover_slide(bundle, 80, 24)
    # ESC from the hostile caption is stripped; what remains is the
    # literal bracket text, which is harmless. The renderer's own paint()
    # wraps the line in its own ANSI codes — exactly two ESC bytes
    # (open + close) from microcopy_line, no more.
    sanitized = bundle["microcopy"]["cover_intro"].replace("\x1b", "")
    assert sanitized in out, "literal bracket text survives, hostile ESC gone"
