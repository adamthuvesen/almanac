"""Descriptive hypotheses for zero-shot commit classification.

Each string is a full clause for NLI zero-shot scoring. Exactly one
hypothesis per Conventional-Commits verb token (eleven total).
"""

from __future__ import annotations

from almanac.classifier.rules import VERB_PREFIXES

LABEL_TO_VERB: dict[str, str] = {
    "adds a new feature, capability, model, or data source": "feat",
    "fixes a bug, defect, incorrect behavior, or data quality issue": "fix",
    "updates dependencies, lock files, or third-party package versions": "chore",
    "updates documentation, comments, readme, or descriptions": "docs",
    "removes, deletes, renames, moves, or restructures existing code without changing its behavior": "refactor",
    "adds or updates tests, assertions, or data quality checks": "test",
    "applies formatting, lint-only edits, or purely cosmetic style changes": "style",
    "improves performance, optimizes queries, or reduces cost": "perf",
    "updates build scripts, packaging, compilers, or local development tooling": "build",
    "changes continuous integration, github workflows, or release automation": "ci",
    "undoes a specific earlier commit": "revert",
}

CANDIDATE_LABELS: list[str] = list(LABEL_TO_VERB.keys())

assert set(LABEL_TO_VERB.values()) == set(VERB_PREFIXES)
assert len(LABEL_TO_VERB) == len(VERB_PREFIXES)
