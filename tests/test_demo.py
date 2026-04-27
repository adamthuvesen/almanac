from __future__ import annotations

from almanac.classifier import BUNDLE_VERB_KEYS
from almanac.demo import make_demo_bundle
from almanac.microcopy import SLOTS as MICROCOPY_SLOTS
from almanac.stats import HIGHLIGHT_KEYS


def test_make_demo_bundle_schema():
    bundle = make_demo_bundle()
    assert bundle["schema_version"] == 1
    assert set(bundle["verbs"].keys()) == set(BUNDLE_VERB_KEYS)
    assert 500 <= bundle["commit_count"] <= 5000
    assert len(bundle["authors"]) >= 3


def test_make_demo_bundle_is_deterministic():
    a = make_demo_bundle()
    b = make_demo_bundle()
    assert a == b


def test_make_demo_bundle_attaches_highlights_and_microcopy():
    bundle = make_demo_bundle()
    h = bundle["highlights"]
    for key in HIGHLIGHT_KEYS:
        assert key in h
    m = bundle["microcopy"]
    for slot in MICROCOPY_SLOTS:
        assert slot in m
    assert h["peak_hour"] is not None
    assert h["peak_hour"]["hour"] == 16
    assert h["busiest_day"] is not None
    assert h["dominant_verb"] is not None
    assert h["comeback"] is not None
    assert m["cadence_caption"] is not None
    assert m["verbs_caption"] is not None
    assert m["quiet_caption"] is not None
    assert m["comeback_caption"] is not None
