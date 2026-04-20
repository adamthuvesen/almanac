import hashlib
import json
import re
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from almanac.cli import main

REPO = Path(__file__).parent.parent


def test_html_out_writes_file_and_skips_browser(tmp_path):
    runner = CliRunner()
    target = tmp_path / "wrap.html"
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(
            main,
            [
                "--html-out",
                str(target),
                "--repo",
                str(REPO),
                "--year",
                "2025",
                "--classifier",
                "rules",
            ],
        )
    assert result.exit_code == 0, result.output
    assert target.exists(), "output file not written"
    text = target.read_text(encoding="utf-8")
    assert text.startswith("<!doctype html>")
    assert str(target) in (result.stderr or "")
    mock_open.assert_not_called()


def test_html_default_writes_to_temp_and_opens_browser(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    runner = CliRunner()
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(
            main,
            ["--html", "--repo", str(REPO), "--year", "2025", "--classifier", "rules"],
        )
    assert result.exit_code == 0, result.output
    mock_open.assert_called_once()
    url = mock_open.call_args.args[0]
    assert url.startswith("file://")
    written = Path(url[len("file://") :])
    assert written.exists()
    assert written.parent == tmp_path


def test_html_out_combined_with_html_still_skips_browser(tmp_path):
    runner = CliRunner()
    target = tmp_path / "wrap.html"
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(
            main,
            [
                "--html",
                "--html-out",
                str(target),
                "--repo",
                str(REPO),
                "--year",
                "2025",
                "--classifier",
                "rules",
            ],
        )
    assert result.exit_code == 0, result.output
    assert target.exists()
    mock_open.assert_not_called()


def test_json_wins_over_html(tmp_path):
    runner = CliRunner()
    target = tmp_path / "wrap.html"
    with patch("webbrowser.open") as mock_open:
        result = runner.invoke(
            main,
            [
                "--json",
                "--html",
                "--html-out",
                str(target),
                "--repo",
                str(REPO),
                "--year",
                "2025",
                "--classifier",
                "rules",
            ],
        )
    assert result.exit_code == 0, result.output
    bundle = json.loads(result.stdout)
    assert bundle["schema_version"] == 1
    assert not target.exists(), "HTML file should NOT be written when --json wins"
    assert "json wins" in (result.stderr or "")
    mock_open.assert_not_called()


def _extract_bundle(html: str) -> dict:
    m = re.search(
        r'<script id="almanac-bundle" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert m, "no bundle script in output"
    return json.loads(m.group(1))


def test_default_run_has_no_gravatar_hash(tmp_path):
    runner = CliRunner()
    target = tmp_path / "wrap.html"
    with patch("webbrowser.open"):
        result = runner.invoke(
            main,
            [
                "--html-out",
                str(target),
                "--repo",
                str(REPO),
                "--year",
                "2026",
                "--classifier",
                "rules",
            ],
        )
    assert result.exit_code == 0, result.output
    html = target.read_text(encoding="utf-8")
    bundle = _extract_bundle(html)
    assert bundle["authors"], "fixture repo should have authors"
    # No author entry has an avatar_hash, so the template's `if (hash)`
    # branch is never taken and no network request is ever issued.
    for author in bundle["authors"]:
        assert "avatar_hash" not in author


def test_gravatar_flag_emits_hashes(tmp_path):
    runner = CliRunner()
    target = tmp_path / "wrap.html"
    with patch("webbrowser.open"):
        result = runner.invoke(
            main,
            [
                "--gravatar",
                "--html-out",
                str(target),
                "--repo",
                str(REPO),
                "--year",
                "2026",
                "--classifier",
                "rules",
            ],
        )
    assert result.exit_code == 0, result.output
    bundle = _extract_bundle(target.read_text(encoding="utf-8"))
    assert bundle["authors"], "fixture repo should have authors"
    first = bundle["authors"][0]
    assert "avatar_hash" in first
    expected = hashlib.md5(
        first["emails"][0].strip().lower().encode("utf-8")
    ).hexdigest()
    assert first["avatar_hash"] == expected
    assert re.fullmatch(r"[0-9a-f]{32}", first["avatar_hash"])


def _repo_head_author() -> tuple[str, str]:
    import subprocess

    out = subprocess.check_output(
        ["git", "-C", str(REPO), "log", "-1", "--pretty=format:%an%x1f%ae"],
        text=True,
    )
    name, email = out.split("\x1f", 1)
    return name, email


def _swapcase_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local.title()}@{domain.title()}"


def test_author_filter_case_insensitive_email(tmp_path):
    _, email = _repo_head_author()
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--json",
            "--author",
            _swapcase_email(email),
            "--repo",
            str(REPO),
            "--year",
            "2026",
            "--classifier",
            "rules",
        ],
    )
    assert result.exit_code == 0, result.output
    bundle = json.loads(result.stdout)
    assert bundle["commit_count"] >= 1


def test_author_filter_case_insensitive_name(tmp_path):
    name, _ = _repo_head_author()
    runner = CliRunner()

    def run(author: str) -> dict:
        res = runner.invoke(
            main,
            [
                "--json",
                "--author",
                author,
                "--repo",
                str(REPO),
                "--year",
                "2026",
                "--classifier",
                "rules",
            ],
        )
        assert res.exit_code == 0, res.output
        return json.loads(res.stdout)

    bundle_lc = run(name.lower())
    bundle_uc = run(name.upper())
    assert bundle_lc["commit_count"] == bundle_uc["commit_count"]


def test_merge_count_consistent_with_filtered_commits(tmp_path):
    # Without --author, merge_count is derivable from the parents lists.
    # The invariant: merge_count <= commit_count and the same run with
    # --include-merges reports the same merge_count value.
    runner = CliRunner()
    result_no_merges = runner.invoke(
        main,
        [
            "--json",
            "--repo",
            str(REPO),
            "--year",
            "2026",
            "--classifier",
            "rules",
        ],
    )
    assert result_no_merges.exit_code == 0, result_no_merges.output
    bundle_no_merges = json.loads(result_no_merges.stdout)
    # With --no-merges by default, merge_count must be 0.
    assert bundle_no_merges["merge_count"] == 0

    result_with_merges = runner.invoke(
        main,
        [
            "--json",
            "--include-merges",
            "--repo",
            str(REPO),
            "--year",
            "2026",
            "--classifier",
            "rules",
        ],
    )
    assert result_with_merges.exit_code == 0
    bundle_with_merges = json.loads(result_with_merges.stdout)
    assert bundle_with_merges["merge_count"] <= bundle_with_merges["commit_count"]


def test_html_overrides_tty_writes_note(tmp_path):
    runner = CliRunner()
    target = tmp_path / "wrap.html"
    with patch("webbrowser.open"):
        result = runner.invoke(
            main,
            [
                "--tty",
                "--html",
                "--html-out",
                str(target),
                "--repo",
                str(REPO),
                "--year",
                "2025",
                "--classifier",
                "rules",
            ],
        )
    assert result.exit_code == 0, result.output
    assert "html wins" in (result.stderr or "")
    assert target.exists()


def test_invalid_window_exits_nonzero():
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--json",
            "--since",
            "2025-12-31",
            "--until",
            "2025-01-01",
            "--repo",
            str(REPO),
            "--classifier",
            "rules",
        ],
    )
    assert result.exit_code != 0
    assert "cannot be later" in result.output.lower()
