import json
import os

from almanac.renderer.html import _safe_json, render_html, write_html


def _minimal_bundle() -> dict:
    return {
        "schema_version": 1,
        "repo": {"path": "/tmp/x", "name": "demo", "head_sha": "abcdef1234567890"},
        "window": {"since": "2025-01-01", "until": "2025-12-31", "label": "2025"},
        "commit_count": 3,
        "merge_count": 0,
        "first_commit": {
            "sha": "deadbeef",
            "ts": "2025-01-02T10:00:00+00:00",
            "subject": "init",
            "author": "Ada",
        },
        "last_commit": None,
        "verbs": {
            "feat": 2,
            "fix": 1,
            "chore": 0,
            "docs": 0,
            "refactor": 0,
            "test": 0,
            "style": 0,
            "perf": 0,
            "build": 0,
            "ci": 0,
            "revert": 0,
            "unclear": 0,
        },
        "by_dow": [1, 0, 0, 1, 1, 0, 0],
        "by_hour": [0] * 24,
        "lines_added": 100,
        "lines_removed": 5,
        "biggest_commit": {
            "sha": "x",
            "delta": 50,
            "subject": "big",
            "ts": "2025-02-01",
        },
        "longest_streak_days": 2,
        "longest_gap_days": 30,
        "files_by_churn": [{"path": "src/a.py", "edits": 3, "lines": 80}],
        "languages": [{"ext": ".py", "lines": 95, "share": 1.0}],
        "authors": [
            {
                "name": "Ada",
                "emails": ["ada@x"],
                "commits": 3,
                "lines_added": 100,
                "lines_removed": 5,
                "first_ts": "2025-01-02T10:00:00+00:00",
                "last_ts": "2025-03-01T10:00:00+00:00",
            }
        ],
        "subjects_sample": ["init", "feat: x", "fix: y"],
        "commits_per_day": [
            {"date": "2025-01-01", "count": 0},
            {"date": "2025-01-02", "count": 1},
        ],
    }


def test_render_html_returns_full_document():
    out = render_html(_minimal_bundle())
    assert out.startswith("<!doctype html>")
    assert 'data-theme="classic"' in out
    assert "</html>" in out


def test_render_html_includes_data_theme_when_midnight():
    out = render_html(_minimal_bundle(), theme="midnight")
    assert 'data-theme="midnight"' in out


def test_render_html_default_theme_is_classic():
    out = render_html(_minimal_bundle())
    assert 'data-theme="classic"' in out


def test_render_html_includes_palette_custom_properties():
    out = render_html(_minimal_bundle())
    for token in ("--cream:", "--ink:", "--rust:", "--sage:", "--ochre:", "--plum:"):
        assert token in out, f"missing palette token {token}"


def test_render_html_inlines_bundle_json():
    bundle = _minimal_bundle()
    out = render_html(bundle)
    assert 'id="almanac-bundle"' in out
    assert 'type="application/json"' in out
    # The serialized commit_count value should be substituted in.
    assert '"commit_count": 3' in out or '"commit_count":3' in out


def test_render_html_has_no_default_remote_assets():
    out = render_html(_minimal_bundle())
    assert 'src="https://' not in out
    assert 'href="https://' not in out
    assert "fonts.googleapis.com" not in out
    assert "cdn.jsdelivr.net" not in out


def test_render_html_handles_unicode_and_special_chars():
    bundle = _minimal_bundle()
    bundle["first_commit"]["subject"] = "feat: éclair — ✨"
    out = render_html(bundle)
    assert "éclair" in out


def test_write_html_default_path_creates_file(tmp_path, monkeypatch):
    bundle = _minimal_bundle()
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    p = write_html(bundle, None)
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert text.startswith("<!doctype html>")


def test_write_html_explicit_path(tmp_path):
    target = tmp_path / "wrap.html"
    p = write_html(_minimal_bundle(), target)
    assert p == target.resolve()
    assert target.exists()


def test_default_write_filename_includes_window_and_sha(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    p = write_html(_minimal_bundle(), None)
    assert "2025" in p.name
    assert "abcdef1" in p.name
    assert p.suffix == ".html"
    assert p.name.startswith("almanac-demo-2025-abcdef1-")


def test_default_write_refuses_symlink_target(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    # Plant a decoy file that an attacker might try to clobber, and a
    # symlink named like the old predictable output path pointing to it.
    victim = tmp_path / "victim.txt"
    victim.write_text("do-not-touch", encoding="utf-8")
    predictable = tmp_path / "almanac-demo-2025-abcdef1.html"
    os.symlink(victim, predictable)

    p = write_html(_minimal_bundle(), None)

    # NamedTemporaryFile uses O_EXCL + a random suffix, so the symlink
    # target must be untouched and the real report lives elsewhere.
    assert p != predictable
    assert victim.read_text(encoding="utf-8") == "do-not-touch"
    assert p.exists()
    assert p.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_bundle_with_closing_script_tag_does_not_break_out():
    bundle = _minimal_bundle()
    bundle["first_commit"]["subject"] = "</script><img src=x onerror=alert(1)>"
    out = render_html(bundle)
    # The dangerous substring must not appear verbatim in the rendered HTML;
    # it must be escaped as <\/script>.
    assert "</script><img src=x" not in out
    assert "<\\/script><img src=x" in out
    # The bundle script block itself is still present exactly once, and the
    # template's own </script> closers remain intact.
    assert out.count('id="almanac-bundle"') == 1


def test_no_inline_onerror_in_rendered_html():
    bundle = _minimal_bundle()
    bundle["authors"] = [
        {
            "name": "Alice Cooper",
            "emails": ["alice@example.com"],
            "commits": 2,
            "lines_added": 10,
            "lines_removed": 1,
            "first_ts": "2025-01-02T10:00:00+00:00",
            "last_ts": "2025-03-01T10:00:00+00:00",
        },
        {
            "name": "Bob",
            "emails": ["bob@example.com"],
            "commits": 1,
            "lines_added": 5,
            "lines_removed": 0,
            "first_ts": "2025-01-02T10:00:00+00:00",
            "last_ts": "2025-03-01T10:00:00+00:00",
        },
    ]
    out = render_html(bundle)
    assert "onerror=" not in out
    assert "cryptoMd5" not in out


def test_initials_with_backslash_and_quote_do_not_break():
    bundle = _minimal_bundle()
    bundle["authors"] = [
        {
            "name": "A\\' Bob",
            "emails": ["a@x"],
            "commits": 1,
            "lines_added": 1,
            "lines_removed": 0,
            "first_ts": "2025-01-02T10:00:00+00:00",
            "last_ts": "2025-03-01T10:00:00+00:00",
        },
    ]
    out = render_html(bundle)
    # Name flows into the JSON bundle (client-side code HTML-escapes it
    # at render time via escapeHtml). What matters here is that no
    # inline event handler references author-derived data.
    assert "onerror=" not in out
    # The name survives JSON encoding without corrupting the script block.
    assert '"A\\\\\' Bob"' in out


def test_safe_json_roundtrips_valid_json():
    bundle = _minimal_bundle()
    bundle["first_commit"]["subject"] = "mix </script> and \u2028 and \u2029"
    escaped = _safe_json(bundle)
    # `JSON.parse` in the browser would accept `<\/`; Python's json.loads
    # also accepts it because `\/` is a valid escape in JSON strings.
    parsed = json.loads(escaped)
    assert parsed == bundle


def test_render_html_does_not_break_on_dollar_signs_in_data():
    bundle = _minimal_bundle()
    bundle["first_commit"]["subject"] = "fix: $PATH handling and $BUNDLE_JSON literal"
    out = render_html(bundle)
    # safe_substitute leaves stray $X alone, so the JSON content is preserved
    assert "$PATH" in out


def _bundle_with_microcopy(slots: dict[str, str | None]) -> dict:
    bundle = _minimal_bundle()
    bundle["microcopy"] = {
        "cover_intro": None,
        "numbers_caption": None,
        "cadence_caption": None,
        "top_files_caption": None,
        "verbs_caption": None,
        "quiet_caption": None,
        "comeback_caption": None,
        "closer_signoff": None,
    }
    bundle["microcopy"].update(slots)
    return bundle


def test_render_html_includes_caption_helper():
    out = render_html(_minimal_bundle())
    # The caption helper is always defined — only the call sites
    # short-circuit when a slot is null.
    assert "const caption" in out
    assert "slide-caption" in out


def test_render_html_inlines_microcopy_when_present():
    bundle = _bundle_with_microcopy(
        {
            "cover_intro": "The 2025 began with initial CLI wiring.",
            "numbers_caption": "1,240 commits, 12,431 added, 8,019 removed.",
            "cadence_caption": "Most likely to ship at 11 PM.",
            "top_files_caption": "stats.py had a year.",
            "verbs_caption": "Mostly feat work — 34% of the year.",
            "comeback_caption": (
                "A quiet spell of 42 days, then back with 9 commits in a fortnight."
            ),
            "closer_signoff": "Closed on ship it after a 14-day streak.",
        }
    )
    out = render_html(bundle)
    # The microcopy strings are embedded in the inlined BUNDLE_JSON.
    assert "Most likely to ship at 11 PM." in out
    assert "stats.py had a year." in out
    assert "Mostly feat work" in out


def test_render_html_microcopy_with_metacharacters_is_safe():
    bundle = _bundle_with_microcopy(
        {"top_files_caption": "foo.py & bar</script> had a year."}
    )
    escaped = _safe_json(bundle)
    # The bundle JSON is wrapped in a <script> tag; _safe_json must escape
    # the closing-script sequence in any user-controlled string.
    assert "</script>" not in escaped
    assert "<\\/script>" in escaped
    # The JS caption() helper runs escapeHtml() on the value before
    # inserting it into the DOM — so the live document never sees a
    # raw </script> tag from a hostile caption.
    out = render_html(bundle)
    assert "escapeHtml" in out


def test_render_html_is_deterministic_for_same_bundle():
    bundle = _bundle_with_microcopy(
        {"cover_intro": "The 2025 began with initial CLI wiring."}
    )
    a = render_html(bundle)
    b = render_html(bundle)
    assert a == b


def test_heatmap_cells_have_data_date_count() -> None:
    out = render_html(_minimal_bundle())
    assert "data-date" in out
    assert "data-count" in out


def test_top_file_bars_have_data_subjects() -> None:
    out = render_html(_minimal_bundle())
    assert "data-subjects" in out
    assert "JSON.stringify" in out


def test_biggest_commit_has_data_sha_date_subject() -> None:
    out = render_html(_minimal_bundle())
    assert "data-sha" in out
    assert 'data-date="' in out or "data-date" in out
    assert "data-subject" in out
    assert "stat-receipt" in out or "data-sha" in out


def test_subjects_with_html_metacharacters_are_safe() -> None:
    bundle = _minimal_bundle()
    bundle["files_by_churn"] = [
        {
            "path": "evil.js",
            "edits": 1,
            "lines": 1,
            "subjects": [
                "bad</script><img src=x onerror=alert(1)",
                "a&b",
                "x<y>z",
            ],
        }
    ]
    out = render_html(bundle)
    assert "</script><img" not in out
    assert "<\\/script>" in out or "<\\/script><img" in out


def test_receipt_js_handlers_present() -> None:
    out = render_html(_minimal_bundle())
    for marker in (
        "heatmap-tooltip",
        "receipts-panel",
        "almanacBindHeatmapReceiptTooltip",
        "almanacSetupInspectableReceipts",
        "almanac-biggest-receipt-popover",
        "almanacCloseAllReceiptOverlays",
    ):
        assert marker in out, f"missing {marker}"
