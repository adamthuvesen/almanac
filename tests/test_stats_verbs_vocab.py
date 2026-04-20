"""Stats bundle exposes the full verb vocabulary."""

from __future__ import annotations

from almanac.classifier import BUNDLE_VERB_KEYS
from almanac.ingest import Commit
from almanac.stats import compute_bundle
from almanac.window import resolve_window


def test_bundle_verbs_exact_keys_no_other():
    window = resolve_window(year=2025, since=None, until=None)
    c = Commit(
        sha="a",
        ts="2025-06-01T12:00:00+00:00",
        author_name="a",
        author_email="a@a",
        parents=[],
        subject="fix: x",
        files=[],
    )
    bundle = compute_bundle(
        [c],
        window,
        {"path": "/", "name": "n", "head_sha": "h"},
        classifier_strategy="rules",
    )
    assert set(bundle["verbs"].keys()) == set(BUNDLE_VERB_KEYS)
    assert bundle["verbs"]["fix"] == 1
    assert "other" not in bundle["verbs"]
