"""Commit subject classifier: rules, zero-shot, or auto."""

from __future__ import annotations

from almanac.classifier import rules
from almanac.classifier.cache import (
    classification_cache_key,
    clear_cache,
    get_cached,
    set_cached,
)
from almanac.classifier.preprocess import preprocess

__all__ = [
    "BUNDLE_VERB_KEYS",
    "classify",
    "clear_cache",
    "has_transformers",
    "reset_auto_strategy",
]

BUNDLE_VERB_KEYS: tuple[str, ...] = (*rules.VERB_PREFIXES, "unclear")

_AUTO_RESOLVED: str | None = None


def reset_auto_strategy() -> None:
    global _AUTO_RESOLVED
    _AUTO_RESOLVED = None


def has_transformers() -> bool:
    try:
        import transformers  # noqa: F401
    except ImportError:
        return False
    return True


def _resolve_auto() -> str:
    global _AUTO_RESOLVED
    if _AUTO_RESOLVED is None:
        _AUTO_RESOLVED = "zeroshot" if has_transformers() else "rules"
    return _AUTO_RESOLVED


def _ensure_zeroshot_allowed() -> None:
    if not has_transformers():
        raise ImportError(
            "Zero-shot classification requires optional ML dependencies. "
            "Install with: pip install 'almanac[ml]'"
        )


def _effective_strategy(strategy: str) -> str:
    if strategy == "auto":
        return _resolve_auto()
    return strategy


def classify(subject: str, body: str | None, *, strategy: str) -> tuple[str, float]:
    eff = _effective_strategy(strategy)
    if strategy == "zeroshot":
        _ensure_zeroshot_allowed()

    clean = preprocess(subject)
    key = classification_cache_key(clean, body)
    cached = get_cached(key)
    if cached is not None:
        return cached

    if eff == "rules":
        result = rules.classify_commit(clean, body)
    else:
        from almanac.classifier import zeroshot

        result = zeroshot.classify_commit(clean, body)

    set_cached(key, result)
    return result
