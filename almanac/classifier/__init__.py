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
    "classify_batch",
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
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except (ImportError, OSError):
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


def _resolve_strategy(strategy: str) -> str:
    if strategy == "zeroshot":
        _ensure_zeroshot_allowed()
    return _resolve_auto() if strategy == "auto" else strategy


def classify(subject: str, body: str | None, *, strategy: str) -> tuple[str, float]:
    eff = _resolve_strategy(strategy)
    clean = preprocess(subject)
    key = classification_cache_key(eff, clean, body)
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


def classify_batch(subjects: list[str], *, strategy: str) -> list[tuple[str, float]]:
    eff = _resolve_strategy(strategy)

    clean_subjects = [preprocess(s) for s in subjects]
    results: list[tuple[str, float] | None] = [None] * len(subjects)
    pending_indices: list[int] = []
    pending_clean: list[str] = []
    pending_keys: list[str] = []

    for i, clean in enumerate(clean_subjects):
        key = classification_cache_key(eff, clean, None)
        cached = get_cached(key)
        if cached is not None:
            results[i] = cached
        else:
            pending_indices.append(i)
            pending_clean.append(clean)
            pending_keys.append(key)

    if pending_clean:
        if eff == "rules":
            batch_results = [rules.classify_commit(s, None) for s in pending_clean]
        else:
            from almanac.classifier import zeroshot

            batch_results = zeroshot.classify_batch(pending_clean)

        for idx, key, result in zip(pending_indices, pending_keys, batch_results):
            set_cached(key, result)
            results[idx] = result

    out: list[tuple[str, float]] = []
    for r in results:
        if r is None:
            raise RuntimeError("classify_batch produced an unfilled result slot")
        out.append(r)
    return out
