"""First-verb rule layer — scenarios from the commit-classifier spec."""

from __future__ import annotations

import pytest

from almanac.classifier import classify, clear_cache, reset_auto_strategy
from almanac.classifier.rules import match_first_verb


@pytest.fixture(autouse=True)
def _reset():
    clear_cache()
    reset_auto_strategy()
    yield
    clear_cache()
    reset_auto_strategy()


@pytest.mark.parametrize(
    "first_word,expected_verb",
    [
        ("add", "feat"),
        ("adding", "feat"),
        ("adds", "feat"),
        ("added", "feat"),
        ("introduce", "feat"),
        ("introduces", "feat"),
        ("implement", "feat"),
        ("implements", "feat"),
        ("remove", "refactor"),
        ("removes", "refactor"),
        ("removed", "refactor"),
        ("delete", "refactor"),
        ("deletes", "refactor"),
        ("deleted", "refactor"),
        ("drop", "refactor"),
        ("drops", "refactor"),
        ("dropped", "refactor"),
        ("rename", "refactor"),
        ("renames", "refactor"),
        ("renamed", "refactor"),
        ("move", "refactor"),
        ("moves", "refactor"),
        ("moved", "refactor"),
        ("migrate", "refactor"),
        ("migrates", "refactor"),
        ("migrated", "refactor"),
        ("refactor", "refactor"),
        ("refactors", "refactor"),
        ("refactored", "refactor"),
        ("revert", "revert"),
        ("reverts", "revert"),
        ("reverted", "revert"),
        ("fix", "fix"),
        ("fixes", "fix"),
        ("fixed", "fix"),
        ("bump", "chore"),
        ("bumps", "chore"),
        ("bumped", "chore"),
        ("upgrade", "chore"),
        ("upgrades", "chore"),
        ("upgraded", "chore"),
    ],
)
def test_first_verb_rule_matches(first_word: str, expected_verb: str) -> None:
    result = match_first_verb(f"{first_word} something")
    assert result == (expected_verb, 1.0)


def test_first_verb_case_insensitive() -> None:
    assert match_first_verb("ADD new thing") == ("feat", 1.0)
    assert match_first_verb("Remove old thing") == ("refactor", 1.0)


def test_update_has_default_refactor_mapping() -> None:
    # As of expand-classifier-rules, `update` defaults to refactor.
    # Bigram overrides (e.g. "update readme" -> docs) run before
    # first-verb and are covered in test_classifier_rules.py.
    assert match_first_verb("update the API") == ("refactor", 1.0)


def test_change_has_default_refactor_mapping() -> None:
    assert match_first_verb("change the API") == ("refactor", 1.0)


def test_rules_strategy_uses_first_verb() -> None:
    v, s = classify("add new segment model", None, strategy="rules")
    assert v == "feat"
    assert s == 1.0


def test_rules_strategy_remove_resolves_to_refactor() -> None:
    v, s = classify("remove files for dropped tables", None, strategy="rules")
    assert v == "refactor"
    assert s == 1.0


def test_grant_resolves_to_chore() -> None:
    v, s = classify("grant access to prod", None, strategy="rules")
    assert v == "chore"
    assert s == 1.0


def test_rotate_resolves_to_chore() -> None:
    v, s = classify("rotate fivetran snowflake rsa keys", None, strategy="rules")
    assert v == "chore"
    assert s == 1.0
