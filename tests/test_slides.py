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
    # Still shouldn't raise or return empty
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
