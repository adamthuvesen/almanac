"""Within-process classification cache keyed by subject + body hash."""

from __future__ import annotations

import hashlib

_CACHE: dict[str, tuple[str, float]] = {}


def classification_cache_key(strategy: str, subject: str, body: str | None) -> str:
    payload = strategy + "\n" + subject + "\n" + (body or "")
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def get_cached(key: str) -> tuple[str, float] | None:
    return _CACHE.get(key)


def set_cached(key: str, value: tuple[str, float]) -> None:
    _CACHE[key] = value


def clear_cache() -> None:
    _CACHE.clear()
