from __future__ import annotations

import pytest

from almanac.classifier import (
    classify,
    classify_batch,
    clear_cache,
    reset_auto_strategy,
)


@pytest.fixture(autouse=True)
def _reset():
    clear_cache()
    reset_auto_strategy()
    yield
    clear_cache()
    reset_auto_strategy()


def test_empty_list_returns_empty():
    assert classify_batch([], strategy="rules") == []


def test_all_rules_no_model_needed():
    results = classify_batch(
        ["feat: add thing", "fix: handle error", "chore: bump deps"],
        strategy="rules",
    )
    assert results == [("feat", 1.0), ("fix", 1.0), ("chore", 1.0)]


def test_mixed_rules_and_unclear():
    results = classify_batch(
        ["feat: add thing", "one source missed", "fix: handle error"],
        strategy="rules",
    )
    assert results[0] == ("feat", 1.0)
    assert results[2] == ("fix", 1.0)
    assert results[1] == ("unclear", 0.0)


def test_order_preservation():
    subjects = [
        "add user model",
        "fix null check",
        "one source missed",
        "feat: ci pipeline",
    ]
    results = classify_batch(subjects, strategy="rules")
    assert len(results) == 4
    assert results[0] == ("feat", 1.0)
    assert results[1] == ("fix", 1.0)
    assert results[2] == ("unclear", 0.0)
    assert results[3] == ("feat", 1.0)


def test_batch_results_are_cached():
    subjects = ["add user model", "fix null check"]
    classify_batch(subjects, strategy="rules")
    results = classify_batch(subjects, strategy="rules")
    assert results == [("feat", 1.0), ("fix", 1.0)]


def test_batch_cache_shared_with_per_subject():
    classify_batch(["add user model"], strategy="rules")
    result = classify("add user model", None, strategy="rules")
    assert result == ("feat", 1.0)


def test_per_subject_cache_hit_used_by_batch():
    classify("fix null check", None, strategy="rules")
    results = classify_batch(["fix null check"], strategy="rules")
    assert results == [("fix", 1.0)]


def test_single_subject_batch():
    results = classify_batch(["refactor old auth"], strategy="rules")
    assert results == [("refactor", 1.0)]
