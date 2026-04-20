"""Within-run classification cache."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from almanac.classifier import classify, clear_cache, reset_auto_strategy
from almanac.classifier import rules as rules_mod
from almanac.classifier import zeroshot as zeroshot_mod


@pytest.fixture(autouse=True)
def _reset_classifier_state():
    clear_cache()
    reset_auto_strategy()
    yield
    clear_cache()
    reset_auto_strategy()


def test_rules_strategy_not_invoked_twice_for_same_subject():
    with patch.object(
        rules_mod, "classify_commit", wraps=rules_mod.classify_commit
    ) as spy:
        classify("hello world", None, strategy="rules")
        classify("hello world", None, strategy="rules")
    assert spy.call_count == 1


def test_zeroshot_strategy_inner_not_invoked_twice_for_same_subject():
    calls = {"n": 0}

    def fake_commit(subject: str, body: str | None = None):
        calls["n"] += 1
        return ("feat", 0.9)

    with (
        patch("almanac.classifier._ensure_zeroshot_allowed", lambda: None),
        patch.object(zeroshot_mod, "classify_commit", side_effect=fake_commit),
    ):
        classify("unique z subject", None, strategy="zeroshot")
        classify("unique z subject", None, strategy="zeroshot")
    assert calls["n"] == 1


def test_prefix_only_variants_share_cache_entry():
    """Two raw subjects that normalise to the same preprocessed form share a cache entry."""
    calls = {"n": 0}

    def fake_commit(subject: str, body: str | None = None):
        calls["n"] += 1
        return ("feat", 0.9)

    with (
        patch("almanac.classifier._ensure_zeroshot_allowed", lambda: None),
        patch.object(zeroshot_mod, "classify_commit", side_effect=fake_commit),
    ):
        r1 = classify("clarify visitor semantics", None, strategy="zeroshot")
        r2 = classify("PROJ 123 clarify visitor semantics", None, strategy="zeroshot")
    assert calls["n"] == 1
    assert r1 == r2
