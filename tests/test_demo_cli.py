from __future__ import annotations

import hashlib
import json
import re
from unittest.mock import patch

from click.testing import CliRunner

from almanac.cli import main


def _extract_bundle(html: str) -> dict:
    m = re.search(
        r'<script id="almanac-bundle" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert m, "no bundle script in output"
    return json.loads(m.group(1))


def test_demo_html_out_classic_theme(tmp_path):
    target = tmp_path / "demo.html"
    runner = CliRunner()
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(
            main,
            ["--demo", "--html-out", str(target)],
        )
    assert result.exit_code == 0, result.output
    assert target.exists()
    text = target.read_text(encoding="utf-8")
    assert 'data-theme="classic"' in text
    mock_open.assert_not_called()


def test_demo_html_omits_gravatar_hashes_by_default(tmp_path):
    target = tmp_path / "demo.html"
    runner = CliRunner()
    with patch("webbrowser.open"):
        result = runner.invoke(
            main,
            ["--demo", "--html-out", str(target)],
        )
    assert result.exit_code == 0, result.output
    bundle = _extract_bundle(target.read_text(encoding="utf-8"))
    assert bundle["authors"]
    for author in bundle["authors"]:
        assert "avatar_hash" not in author


def test_demo_gravatar_flag_emits_hashes(tmp_path):
    target = tmp_path / "demo.html"
    runner = CliRunner()
    with patch("webbrowser.open"):
        result = runner.invoke(
            main,
            ["--demo", "--gravatar", "--html-out", str(target)],
        )
    assert result.exit_code == 0, result.output
    bundle = _extract_bundle(target.read_text(encoding="utf-8"))
    first = bundle["authors"][0]
    expected = hashlib.md5(
        first["emails"][0].strip().lower().encode("utf-8")
    ).hexdigest()
    assert first["avatar_hash"] == expected


def test_demo_html_out_wrapped_theme(tmp_path):
    target = tmp_path / "demo.html"
    runner = CliRunner()
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(
            main,
            ["--demo", "--theme", "wrapped", "--html-out", str(target)],
        )
    assert result.exit_code == 0, result.output
    assert target.exists()
    text = target.read_text(encoding="utf-8")
    assert 'data-theme="wrapped"' in text
    mock_open.assert_not_called()


def test_demo_conflicts_with_repo():
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--demo", "--repo", "/tmp"],
    )
    assert result.exit_code == 1
    err = (result.output or "") + (getattr(result, "stderr", None) or "")
    assert "--demo" in err and "--repo" in err
