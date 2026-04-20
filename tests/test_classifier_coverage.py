"""Pin the rules-strategy unclear rate and runtime on a realistic fixture.

See `tests/fixtures/commit_subjects_sample.txt` for the source data.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from almanac.classifier import classify, clear_cache, reset_auto_strategy

FIXTURE = Path(__file__).parent / "fixtures" / "commit_subjects_sample.txt"
UNCLEAR_CEILING = 0.22  # 2-point buffer above 20% target
WALL_TIME_CEILING_MS = 500


@pytest.fixture(autouse=True)
def _reset_classifier_state():
    clear_cache()
    reset_auto_strategy()
    yield
    clear_cache()
    reset_auto_strategy()


def _load_fixture() -> list[str]:
    lines = FIXTURE.read_text().splitlines()
    return [ln for ln in lines if ln and not ln.startswith("#")]


def test_fixture_has_enough_subjects():
    subjects = _load_fixture()
    assert len(subjects) >= 200, f"fixture has only {len(subjects)} subjects"


def test_fixture_unclear_rate_below_ceiling():
    subjects = _load_fixture()
    unclear = sum(
        1 for s in subjects if classify(s, None, strategy="rules")[0] == "unclear"
    )
    rate = unclear / len(subjects)
    assert rate <= UNCLEAR_CEILING, (
        f"unclear rate {rate:.1%} exceeds ceiling {UNCLEAR_CEILING:.0%} "
        f"({unclear}/{len(subjects)})"
    )


def test_fixture_classification_is_fast():
    subjects = _load_fixture()
    # Pre-warm the module once so we measure classification, not import cost.
    classify(subjects[0], None, strategy="rules")
    clear_cache()

    t0 = time.perf_counter()
    for s in subjects:
        classify(s, None, strategy="rules")
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert elapsed_ms <= WALL_TIME_CEILING_MS, (
        f"classification took {elapsed_ms:.0f}ms, exceeds {WALL_TIME_CEILING_MS}ms"
    )
