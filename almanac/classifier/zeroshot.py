"""Transformer zero-shot classification (optional `almanac[ml]` extra)."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from almanac.classifier import rules
from almanac.classifier.labels import CANDIDATE_LABELS, LABEL_TO_VERB

MODEL_ID = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
MODEL_REVISION = "8e7e5af5983a0ddb1a5b45a38b129ab69e2258e8"
ZEROSHOT_CONFIDENCE_THRESHOLD = 0.35
MARGIN_THRESHOLD = 0.05

_PIPELINE: Callable[..., Any] | None = None


def _get_pipeline() -> Callable[..., Any]:
    global _PIPELINE
    if _PIPELINE is not None:
        return _PIPELINE
    import torch
    from transformers import pipeline

    print(
        "Loading zero-shot classifier model "
        "(first use may download ~180MB to the Hugging Face cache; "
        "set HF_HOME to override cache location)...",
        file=sys.stderr,
    )

    common = {"model": MODEL_ID, "revision": MODEL_REVISION}
    device: str | int = "mps" if torch.backends.mps.is_available() else -1
    try:
        _PIPELINE = pipeline("zero-shot-classification", device=device, **common)
    except Exception:
        _PIPELINE = pipeline("zero-shot-classification", device=-1, **common)
    return _PIPELINE


def classify_commit(subject: str, body: str | None = None) -> tuple[str, float]:
    verb, score = rules.classify_commit(subject, body)
    if verb != "unclear":
        return (verb, score)

    pipe = _get_pipeline()
    result = pipe(subject, candidate_labels=CANDIDATE_LABELS, multi_label=False)
    if isinstance(result, list):
        result = result[0]
    top = result["labels"][0]
    top_score = float(result["scores"][0])
    second_score = float(result["scores"][1]) if len(result["scores"]) > 1 else 0.0

    verb = LABEL_TO_VERB[top]
    if top_score < ZEROSHOT_CONFIDENCE_THRESHOLD:
        return ("unclear", top_score)
    if top_score - second_score < MARGIN_THRESHOLD:
        return ("unclear", top_score)
    return (verb, top_score)
