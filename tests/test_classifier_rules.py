"""Rules (regex) strategy — scenarios from commit-classifier spec."""

from __future__ import annotations

import pytest

from almanac.classifier import classify, clear_cache, reset_auto_strategy


@pytest.fixture(autouse=True)
def _reset_classifier_state():
    clear_cache()
    reset_auto_strategy()
    yield
    clear_cache()
    reset_auto_strategy()


def test_conventional_subject_returns_verb_and_full_confidence():
    v, s = classify("fix(api): handle null payload", None, strategy="rules")
    assert v == "fix"
    assert s == 1.0


def test_free_form_subject_returns_unclear_zero():
    v, s = classify("one source missed", None, strategy="rules")
    assert v == "unclear"
    assert s == 0.0


def test_add_prefix_resolves_via_first_verb_rule():
    v, s = classify("add new org activity segment model", None, strategy="rules")
    assert v == "feat"
    assert s == 1.0


def test_optional_scope_form():
    v, s = classify("docs: update readme", None, strategy="rules")
    assert v == "docs"
    assert s == 1.0


def test_case_insensitive_prefix():
    v, s = classify("FEAT: thing", None, strategy="rules")
    assert v == "feat"
    assert s == 1.0


def test_all_eleven_prefixes_match():
    for verb in (
        "feat",
        "fix",
        "chore",
        "docs",
        "refactor",
        "test",
        "style",
        "perf",
        "build",
        "ci",
        "revert",
    ):
        v, s = classify(f"{verb}: do something", None, strategy="rules")
        assert v == verb
        assert s == 1.0


def test_scope_paren_required_shape():
    v, s = classify("fix(api): msg", None, strategy="rules")
    assert v == "fix"
    assert s == 1.0


def test_colon_without_space_normalised_by_preprocessing():
    # Preprocessing inserts the missing space so the CC regex matches.
    v, s = classify("fix:give permission to deploy", None, strategy="rules")
    assert v == "fix"
    assert s == 1.0


def test_breaking_change_exclamation_matches():
    v, s = classify("fix!: breaking change fix", None, strategy="rules")
    assert v == "fix"
    assert s == 1.0


def test_space_before_scope_matches():
    # "chore (PROJ-1498): ..." has a space before the scope parens.
    v, s = classify("chore (PROJ-1498): bump dependencies", None, strategy="rules")
    assert v == "chore"
    assert s == 1.0


def test_breaking_change_with_scope_matches():
    v, s = classify("feat!(api): remove deprecated endpoint", None, strategy="rules")
    assert v == "feat"
    assert s == 1.0


def test_prefix_without_trailer_does_not_match():
    v, s = classify("fix:", None, strategy="rules")
    assert v == "unclear"
