import importlib
import json
import os
import re
import struct
import subprocess
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

REPO = Path(__file__).parent.parent


def _sample_bundle() -> dict:
    return {
        "schema_version": 1,
        "repo": {
            "path": "/tmp/x",
            "name": "acme-platform",
            "head_sha": "abcdef1234567890",
        },
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
            {"date": "2025-01-05", "count": 2},
        ],
    }


def _empty_bundle() -> dict:
    b = _sample_bundle()
    b["commit_count"] = 0
    b["commits_per_day"] = []
    b["merge_count"] = 0
    b["by_dow"] = [0] * 7
    b["files_by_churn"] = []
    b["languages"] = []
    b["authors"] = []
    b["subjects_sample"] = []
    b["first_commit"] = None
    b["last_commit"] = None
    b["biggest_commit"] = None
    b["lines_added"] = 0
    b["lines_removed"] = 0
    b["verbs"] = {k: 0 for k in b["verbs"]}
    return b


def _png_pixel_dims(path: Path) -> tuple[int, int]:
    b = path.read_bytes()
    if len(b) < 24 or b[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a valid PNG")
    return struct.unpack(">II", b[16:24])


def test_card_dimensions(tmp_path) -> None:
    pytest.importorskip("playwright")
    from almanac.renderer.png import render_png

    out = tmp_path / "c.png"
    render_png(_sample_bundle(), out)
    w, h = _png_pixel_dims(out)
    assert w == 1200
    assert h == 630


def test_png_out_refuses_symlink(tmp_path) -> None:
    pytest.importorskip("playwright")
    from almanac.renderer.png import render_png

    victim = tmp_path / "victim.png"
    victim.write_bytes(b"keep")
    link = tmp_path / "out.png"
    os.symlink(victim, link)
    with pytest.raises(click.ClickException, match="symlink"):
        render_png(_sample_bundle(), link)
    assert victim.read_bytes() == b"keep"


def test_card_contains_repo_name() -> None:
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    from almanac.renderer.png import build_card_html

    html = build_card_html(_sample_bundle())
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.set_content(html, wait_until="load")
        body = page.text_content("body")
        assert body is not None
        assert "acme-platform" in body
        browser.close()


def test_card_makes_no_network_requests() -> None:
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    from almanac.renderer.png import build_card_html

    html = build_card_html(_sample_bundle())
    assert re.search(r'(?:href|src)\s*=\s*["\']https?://', html, re.I) is None, (
        "card HTML should not reference remote http(s) resources"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        external: list[str] = []

        def handle(route, request) -> None:
            u = request.url
            if u.startswith("http://") or u.startswith("https://"):
                external.append(u)
            route.continue_()

        page.route("**/*", handle)
        page.set_content(html, wait_until="load")
        assert not external, f"unexpected remote requests: {external}"
        browser.close()


def test_empty_window_card_renders_no_commits_state() -> None:
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    from almanac.renderer.png import build_card_html

    html = build_card_html(_empty_bundle())
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 630})
        page.set_content(html, wait_until="load")
        body = page.text_content("body")
        assert body is not None
        assert "no commits" in body.lower()
        browser.close()


def test_cli_png_smoke_out(tmp_path) -> None:
    pytest.importorskip("playwright")
    from almanac.cli import main

    out = tmp_path / "x.png"
    runner = CliRunner()
    r = runner.invoke(
        main,
        ["--png", "--png-out", str(out), "--repo", str(REPO), "--classifier", "rules"],
    )
    assert r.exit_code == 0, r.output
    assert out.exists()
    w, h = _png_pixel_dims(out)
    assert w == 1200 and h == 630


def test_cli_png_fails_gracefully_without_playwright(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from almanac.cli import main

    orig = importlib.import_module

    def _fake_import(name: str, package: str | None = None) -> object:
        if name == "playwright.sync_api":
            raise ImportError("simulated missing playwright")
        return orig(name, package)

    monkeypatch.setattr(importlib, "import_module", _fake_import)
    sp_run = subprocess.run
    called_git: list[bool] = []

    def _no_git(*a: object, **k: object) -> subprocess.CompletedProcess[bytes]:  # type: ignore[override]
        cmd = a[0] if a else k.get("args")
        if cmd and list(cmd)[:1] == ["git"]:
            called_git.append(True)
        return sp_run(*a, **k)  # type: ignore[misc]

    monkeypatch.setattr(subprocess, "run", _no_git)
    r = CliRunner()
    res = r.invoke(
        main,
        ["--png", "--png-out", str(tmp_path / "n.png")],
    )
    assert res.exit_code == 1
    combined = (res.output or "") + (res.stderr or "")
    assert "almanac[png]" in combined
    assert "playwright" in combined.lower()
    assert "install chromium" in combined.lower()
    assert not called_git


def test_cli_json_png_does_not_require_playwright(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from almanac.cli import main

    orig = importlib.import_module

    def _fake_import(name: str, package: str | None = None) -> object:
        if name == "playwright.sync_api":
            raise ImportError("simulated missing playwright")
        return orig(name, package)

    monkeypatch.setattr(importlib, "import_module", _fake_import)
    runner = CliRunner()
    res = runner.invoke(
        main,
        ["--json", "--png", "--repo", str(REPO), "--classifier", "rules"],
    )
    assert res.exit_code == 0, res.output
    assert "json wins" in (res.stderr or "") or "json wins" in (res.output or "")
    out = res.output or ""
    json_start = out.find("{")
    assert json_start != -1, out
    bundle = json.loads(out[json_start:])
    assert bundle["schema_version"] == 1
