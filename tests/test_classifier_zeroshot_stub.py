"""Zeroshot path with stubbed pipeline (no model download)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from almanac.classifier import classify, clear_cache, reset_auto_strategy
from almanac.classifier.labels import LABEL_TO_VERB

_PATCH_ENSURE = "almanac.classifier._ensure_zeroshot_allowed"


@pytest.fixture(autouse=True)
def _reset_classifier_state():
    clear_cache()
    reset_auto_strategy()
    yield
    clear_cache()
    reset_auto_strategy()


def _stub_pipeline(label: str, top_score: float, second_score: float = 0.0):
    """Return a fake pipeline callable with two-score output for margin testing."""
    labels = list(LABEL_TO_VERB.keys())
    # Put the target label first; fill remaining with dummy scores.
    other_label = next(candidate for candidate in labels if candidate != label)

    def pipe(subject, candidate_labels=None, multi_label=False):
        return {
            "labels": [label, other_label],
            "scores": [top_score, second_score],
        }

    return pipe


@pytest.mark.parametrize(
    "subject,label,top_score,second_score,expected_verb",
    [
        # Subjects that reach the model (no first-verb or dep-pattern match)
        (
            "clarify visitor and registration semantics",
            "renames, moves, restructures, or cleans up code without changing behavior",
            0.60,
            0.20,
            "refactor",
        ),
        (
            "one source missed",
            "fixes a bug, defect, incorrect behavior, or data quality issue",
            0.72,
            0.15,
            "fix",
        ),
    ],
)
def test_free_form_maps_hypothesis_to_verb(
    subject, label, top_score, second_score, expected_verb
):
    assert LABEL_TO_VERB[label] == expected_verb
    with (
        patch(_PATCH_ENSURE, lambda: None),
        patch(
            "almanac.classifier.zeroshot._get_pipeline",
            return_value=_stub_pipeline(label, top_score, second_score),
        ),
    ):
        v, s = classify(subject, None, strategy="zeroshot")
    assert v == expected_verb
    assert s == pytest.approx(top_score)


def test_low_confidence_collapses_to_unclear():
    label = "adds a new feature, capability, model, or data source"
    with (
        patch(_PATCH_ENSURE, lambda: None),
        patch(
            "almanac.classifier.zeroshot._get_pipeline",
            return_value=_stub_pipeline(label, 0.22, 0.10),
        ),
    ):
        v, s = classify("ambiguous subject here", None, strategy="zeroshot")
    assert v == "unclear"
    assert s == pytest.approx(0.22)


def test_tight_margin_collapses_to_unclear():
    """Top 0.41, second 0.40 — margin < 0.05 → unclear."""
    label = "adds a new feature, capability, model, or data source"
    with (
        patch(_PATCH_ENSURE, lambda: None),
        patch(
            "almanac.classifier.zeroshot._get_pipeline",
            return_value=_stub_pipeline(label, 0.41, 0.40),
        ),
    ):
        v, s = classify("ambiguous subject here 2", None, strategy="zeroshot")
    assert v == "unclear"
    assert s == pytest.approx(0.41)


def test_comfortable_margin_returns_top_verb():
    """Top 0.55, second 0.20 — margin 0.35 > 0.05 → feat."""
    label = "adds a new feature, capability, model, or data source"
    with (
        patch(_PATCH_ENSURE, lambda: None),
        patch(
            "almanac.classifier.zeroshot._get_pipeline",
            return_value=_stub_pipeline(label, 0.55, 0.20),
        ),
    ):
        v, s = classify("ambiguous subject here 3", None, strategy="zeroshot")
    assert v == "feat"
    assert s == pytest.approx(0.55)


def test_clear_margin_above_threshold_survives():
    """Margin 0.10 (> 0.05) — top verb should survive."""
    label = "fixes a bug, defect, incorrect behavior, or data quality issue"
    with (
        patch(_PATCH_ENSURE, lambda: None),
        patch(
            "almanac.classifier.zeroshot._get_pipeline",
            return_value=_stub_pipeline(label, 0.50, 0.40),
        ),
    ):
        v, s = classify("something weird 4", None, strategy="zeroshot")
    assert v == "fix"
    assert s == pytest.approx(0.50)


def test_conventional_prefix_skips_model():
    pipe_calls = []

    def pipe(subject, candidate_labels=None, multi_label=False):
        pipe_calls.append(subject)
        return {
            "labels": ["updates documentation, comments, readme, or descriptions"],
            "scores": [0.99, 0.01],
        }

    with (
        patch(_PATCH_ENSURE, lambda: None),
        patch("almanac.classifier.zeroshot._get_pipeline", return_value=pipe),
    ):
        v, s = classify("docs: update readme", None, strategy="zeroshot")
    assert (v, s) == ("docs", 1.0)
    assert pipe_calls == []


def test_first_verb_rule_skips_model():
    pipe_calls = []

    def pipe(subject, candidate_labels=None, multi_label=False):
        pipe_calls.append(subject)
        return {"labels": [], "scores": []}

    with (
        patch(_PATCH_ENSURE, lambda: None),
        patch("almanac.classifier.zeroshot._get_pipeline", return_value=pipe),
    ):
        v, s = classify("rename old model to new", None, strategy="zeroshot")
    assert (v, s) == ("refactor", 1.0)
    assert pipe_calls == []


def test_zeroshot_without_transformers_raises():
    import builtins

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "transformers":
            raise ModuleNotFoundError("No module named 'transformers'")
        return real_import(name, globals, locals, fromlist, level)

    with patch.object(builtins, "__import__", fake_import):
        with pytest.raises(ImportError, match=r"pip install 'almanac\[ml\]'"):
            classify("x", None, strategy="zeroshot")
