import json
from pathlib import Path

from click.testing import CliRunner

from almanac.cli import main

REPO = Path(__file__).parent.parent


def test_smoke_json_self():
    runner = CliRunner()
    result = runner.invoke(
        main, ["--json", "--repo", str(REPO), "--classifier", "rules"]
    )
    assert result.exit_code == 0, result.output
    bundle = json.loads(result.output)
    assert bundle["schema_version"] == 1
    assert "subjects_sample" in bundle
    assert isinstance(bundle["subjects_sample"], list)
    from almanac.stats import HIGHLIGHT_KEYS

    assert "highlights" in bundle
    assert set(bundle["highlights"].keys()) == set(HIGHLIGHT_KEYS)
    # Self-test: this repo has commits, so the always-derivable highlights
    # (first/last/biggest/streak/busiest_day/peak_hour/most_touched_file/
    # dominant_verb) must be non-null. longest_quiet and comeback may be
    # null depending on the repo's commit-date distribution.
    for key in (
        "first_commit",
        "last_commit",
        "biggest_commit",
        "longest_streak",
        "busiest_day",
        "peak_hour",
        "most_touched_file",
        "dominant_verb",
    ):
        assert bundle["highlights"][key] is not None, key


def test_smoke_summary_self():
    runner = CliRunner()
    result = runner.invoke(main, ["--repo", str(REPO), "--classifier", "rules"])
    assert result.exit_code == 0, result.output
    lines = result.output.strip().splitlines()
    assert len(lines) == 1
