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


# --- Expanded first-verb vocabulary (see commit-classifier spec) ---


@pytest.mark.parametrize(
    "subject,expected",
    [
        # Restructure-family — default to refactor
        ("update capture point category", "refactor"),
        ("change region_territory to just region", "refactor"),
        ("propagate sensitivity tag downstream", "refactor"),
        ("align column order for experiment ctes", "refactor"),
        ("simplify and rename last_activity", "refactor"),
        ("cluster prep_dim_users on user_id", "refactor"),
        ("set deleted user ip to null", "refactor"),
        ("keep users with another active pending invitation", "refactor"),
        ("default to Unknown", "refactor"),
        ("allow editor previews by recognizing sql_operation", "refactor"),
        ("apply sku macro to stripe prices", "refactor"),
        ("nullify user role if user not in workspace", "refactor"),
        ("cast value to int safely", "refactor"),
        ("exclude vscode settings from git tracking", "refactor"),
        ("provide deletion date for inactive users", "refactor"),
        ("use new prospect_job_seniority event property", "refactor"),
        ("lower email address", "refactor"),
        ("adjust the date filter for future months", "refactor"),
        ("sort key email domain dash tables for pruning", "refactor"),
        ("repoint region from account to lead object", "refactor"),
        ("readd forecast_category", "refactor"),
        ("reupload csv file to fix typo", "refactor"),
        ("dedupe pending workspace memberships", "refactor"),
        ("deduplicate source rows", "refactor"),
        ("merge snowflake-main changes into main", "refactor"),
        ("tidy up Salesforce sources and docs", "refactor"),
        ("reclassify sensitive columns", "refactor"),
        ("enable int_account_subscriptions", "refactor"),
        ("disable int_account_subscriptions", "refactor"),
        ("refine channel grouping logic", "refactor"),
        ("rework segment definition", "refactor"),
        ("improve readability of macro", "refactor"),
        ("enrich braze users", "feat"),
        # CC types as bare leading word
        ("test dbt constraints package", "test"),
        ("docs update for classifier module", "docs"),
        ("document the new API endpoint", "docs"),
        ("documentation pass for stats engine", "docs"),
        ("style: format with ruff", "style"),
        ("format with ruff", "style"),
        ("lint shell scripts", "style"),
        ("optimize query for dim workspaces", "perf"),
        ("package the wheel for release", "build"),
        ("build release wheel", "build"),
    ],
)
def test_expanded_first_verbs(subject, expected):
    v, s = classify(subject, None, strategy="rules")
    assert v == expected, f"{subject!r} -> {v} (expected {expected})"
    assert s == 1.0


# --- Inflected forms for representative new verbs ---


@pytest.mark.parametrize(
    "subject,expected",
    [
        # update: updates / updated / updating
        ("updates column names to snake_case", "refactor"),
        ("updated column names to snake_case", "refactor"),
        ("updating column names to snake_case", "refactor"),
        # change: changes / changed / changing
        ("changes reference to int__", "refactor"),
        ("changed reference to int__", "refactor"),
        ("changing reference to int__", "refactor"),
        # propagate: propagates / propagated / propagating
        ("propagates sensitivity tag downstream", "refactor"),
        ("propagated sensitivity tag downstream", "refactor"),
        ("propagating sensitivity tag downstream", "refactor"),
        # disable: disables / disabled / disabling
        ("disables int_account_subscriptions", "refactor"),
        ("disabled int_account_subscriptions", "refactor"),
        ("disabling int_account_subscriptions", "refactor"),
        # dedupe: dedupes / deduped / deduping
        ("dedupes pending workspace memberships", "refactor"),
        ("deduped pending workspace memberships", "refactor"),
        ("deduping pending workspace memberships", "refactor"),
    ],
)
def test_inflected_new_verbs(subject, expected):
    v, s = classify(subject, None, strategy="rules")
    assert v == expected, f"{subject!r} -> {v} (expected {expected})"
    assert s == 1.0


# --- Bigram overrides (one per override entry) ---


@pytest.mark.parametrize(
    "subject,expected",
    [
        # Docs
        ("update readme for uv syncs", "docs"),
        ("update doc for classifier", "docs"),
        ("update docs for classifier", "docs"),
        ("update documentation for classifier", "docs"),
        ("change readme wording", "docs"),
        # Deps / package / version
        ("update dependency ruff to v0.15.8", "chore"),
        ("update deps to latest", "chore"),
        ("update lock file", "chore"),
        ("update lockfile after ruff bump", "chore"),
        ("update package manifest", "chore"),
        ("update packages to latest", "chore"),
        ("update version pin", "chore"),
        ("bump dependency to v2", "chore"),
        ("pin dependency version", "chore"),
        # Perf
        ("update performance of int workspace membership", "perf"),
        ("change performance budget", "perf"),
        ("improve performance int workspace membership aggregates", "perf"),
        ("improve query plan for dim workspaces", "perf"),
        ("improve speed of cold start", "perf"),
        # Test
        ("update test fixtures", "test"),
        ("update tests for classifier", "test"),
        ("change test severity to warn", "test"),
        ("change severity of pk test to warn", "test"),
        ("change assertion for dim workspaces", "test"),
    ],
)
def test_bigram_overrides(subject, expected):
    v, s = classify(subject, None, strategy="rules")
    assert v == expected, f"{subject!r} -> {v} (expected {expected})"
    assert s == 1.0


def test_bigram_does_not_match_unrelated_second_word():
    # "update the performance stuff" — second token is "the", not a
    # strong-signal keyword. Must fall through to first-verb default.
    v, s = classify("update the performance stuff", None, strategy="rules")
    assert v == "refactor"
    assert s == 1.0


def test_noun_phrase_without_verb_still_unclear():
    # Preserve existing behavior: no-verb subjects stay unclear.
    v, s = classify("one source missed", None, strategy="rules")
    assert v == "unclear"
    assert s == 0.0
