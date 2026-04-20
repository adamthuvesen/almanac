"""Preprocessing scenarios from the commit-classifier spec."""

from __future__ import annotations

import pytest

from almanac.classifier.preprocess import preprocess


@pytest.mark.parametrize(
    "raw,expected",
    [
        # PR number suffix stripped
        ("add new retry logic to worker (#3653)", "add new retry logic to worker"),
        # Bracketed ticket prefix stripped
        ("[JIRA-42] add login validation", "add login validation"),
        # Bare ticket prefix stripped
        ("PROJ 821 add metrics endpoint", "add metrics endpoint"),
        # Branch-name prefix stripped (non-conventional slug)
        (
            "alice/add campaign analytics model",
            "add campaign analytics model",
        ),
        # Conventional commits subject passes through unchanged
        ("feat(api): add endpoint", "feat(api): add endpoint"),
        # Feat/ prefix survives (conventional verb slug)
        ("Feat/expand engagement eligibility", "Feat/expand engagement eligibility"),
        # feat/ (lowercase) also survives
        ("feat/some-feature", "feat/some-feature"),
        # fix/ survives
        ("fix/null-pointer", "fix/null-pointer"),
        # PR suffix with no trailing space
        ("update readme (#42)", "update readme"),
        # ABC-123 bare ticket with dash separator
        ("ABC-123 fix the thing", "fix the thing"),
        # No noise — passes through unchanged
        ("plain old commit message", "plain old commit message"),
        # Branch slug at exactly 20 chars is stripped
        ("a" * 20 + "/do something", "do something"),
        # Branch slug at 21 chars is NOT stripped
        ("a" * 21 + "/do something", "a" * 21 + "/do something"),
        # CC colon-without-space normalisation
        ("fix:give permission to deploy", "fix: give permission to deploy"),
        ("feat:add new endpoint", "feat: add new endpoint"),
        ("fix!:add missing guard", "fix!: add missing guard"),
        # CC colon WITH space is not altered
        ("fix: handle null", "fix: handle null"),
        # JIRA-style bare ticket with colon separator
        ("JIRA-1914: fix login redirect", "fix login redirect"),
        ("PROJ-401: update access control", "update access control"),
    ],
)
def test_preprocess(raw: str, expected: str) -> None:
    assert preprocess(raw) == expected
