"""Slide protocol and filter for the TTY renderer."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Slide(Protocol):
    name: str
    requires: frozenset[str]

    def __call__(self, bundle: dict, width: int, height: int) -> str: ...


def _has_data(bundle: dict, key: str) -> bool:
    v = bundle.get(key)
    if isinstance(v, (list, dict, str, tuple, set, frozenset)):
        return len(v) > 0
    return v is not None


def filter_slides(slides: list[Slide], bundle: dict) -> list[Slide]:
    """Drop slides whose required bundle keys are absent or empty."""
    kept: list[Slide] = []
    for slide in slides:
        reqs = getattr(slide, "requires", frozenset())
        if all(_has_data(bundle, k) for k in reqs):
            kept.append(slide)
    return kept
