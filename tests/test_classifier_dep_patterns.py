"""Dependency-bump compound patterns — scenarios from the commit-classifier spec."""

from __future__ import annotations

import pytest

from almanac.classifier import classify, clear_cache, reset_auto_strategy
from almanac.classifier.rules import match_dependency_bump


@pytest.fixture(autouse=True)
def _reset():
    clear_cache()
    reset_auto_strategy()
    yield
    clear_cache()
    reset_auto_strategy()


@pytest.mark.parametrize(
    "subject",
    [
        # Pattern 1: update dependency <pkg>
        "Update dependency ruff to v0.15.8",
        "bump dependency requests to 2.32.0",
        # Pattern 2: update/bump <pkg> to v<n>
        "bump lightgbm to 4.5.0",
        "update numpy to v1.26.4",
        # Pattern 3: conventional form
        "chore: update dependency ruff v0.15.8",
        "fix: update dependency numpy 2.0.0",
        "build: update dependency setuptools 72",
    ],
)
def test_dependency_bump_matches_chore(subject: str) -> None:
    result = match_dependency_bump(subject)
    assert result == ("chore", 1.0)


def test_dependency_bump_via_rules_strategy() -> None:
    v, s = classify("Update dependency ruff to v0.15.8", None, strategy="rules")
    assert v == "chore"
    assert s == 1.0


def test_plain_update_readme_does_not_match() -> None:
    assert match_dependency_bump("update the readme") is None


def test_prefixed_then_dep_bump() -> None:
    # After preprocessing "[JIRA-1] bump lightgbm to 4.5.0" becomes
    # "bump lightgbm to 4.5.0" which matches first-verb (bump→chore)
    # rather than dep pattern — either way the verdict is chore.
    v, s = classify("[JIRA-1] bump lightgbm to 4.5.0", None, strategy="rules")
    assert v == "chore"
    assert s == 1.0
