"""Opt-in live model test (set ALMANAC_RUN_ML_TESTS=1)."""

from __future__ import annotations

import os

import pytest

from almanac.classifier import classify, clear_cache, reset_auto_strategy

pytestmark = pytest.mark.skipif(
    os.environ.get("ALMANAC_RUN_ML_TESTS") != "1",
    reason="set ALMANAC_RUN_ML_TESTS=1 to run ML integration tests",
)


@pytest.fixture(autouse=True)
def _reset_classifier_state():
    clear_cache()
    reset_auto_strategy()
    yield
    clear_cache()
    reset_auto_strategy()


def test_live_zeroshot_three_subjects():
    v1, _ = classify("fix bug", None, strategy="zeroshot")
    assert v1 == "fix"

    v2, _ = classify("Update dependency ruff", None, strategy="zeroshot")
    assert v2 == "chore"

    v3, _ = classify("add org activity segment model", None, strategy="zeroshot")
    assert v3 == "feat"
