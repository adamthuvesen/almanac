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


def test_smoke_summary_self():
    runner = CliRunner()
    result = runner.invoke(main, ["--repo", str(REPO), "--classifier", "rules"])
    assert result.exit_code == 0, result.output
    lines = result.output.strip().splitlines()
    assert len(lines) == 1
