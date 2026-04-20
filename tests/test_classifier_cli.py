"""CLI --classifier flag."""

from __future__ import annotations

import builtins
from pathlib import Path

from click.testing import CliRunner

from almanac.cli import main

REPO = Path(__file__).parent.parent


def test_invalid_classifier_exits_nonzero():
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["--classifier", "wizard", "--repo", str(REPO), "--year", "2025"],
    )
    assert result.exit_code != 0
    combined = (result.stderr or "") + (result.stdout or "")
    assert "zeroshot" in combined.lower()


def test_zeroshot_without_ml_exits_before_git(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "transformers":
            raise ModuleNotFoundError("No module named 'transformers'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    runner = CliRunner()
    result = runner.invoke(main, ["--classifier", "zeroshot", "--year", "2025"])
    assert result.exit_code != 0
    assert "almanac[ml]" in (result.stderr or "")


def test_classifier_default_is_auto_in_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--classifier" in result.output
    assert "auto" in result.output
