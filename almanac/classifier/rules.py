"""Regex-based Conventional Commits classification (rules strategy)."""

from __future__ import annotations

import re

VERB_PREFIXES: tuple[str, ...] = (
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
)

_VERB_PATTERN = re.compile(
    r"^(" + "|".join(VERB_PREFIXES) + r")\s*!?(\(.*?\))?: .*",
    re.IGNORECASE,
)

# First-token → verb mappings for unambiguous English verbs (>95% precision).
# Keys are lowercase first words; values are Conventional Commits verb tokens.
FIRST_VERB_RULES: dict[str, str] = {
    # New capability
    "add": "feat",
    "adding": "feat",
    "adds": "feat",
    "added": "feat",
    "introduce": "feat",
    "introduces": "feat",
    "implement": "feat",
    "implements": "feat",
    "create": "feat",
    "creates": "feat",
    "created": "feat",
    "extend": "feat",
    "extends": "feat",
    "extended": "feat",
    "extending": "feat",
    # Restructuring / moving code
    "remove": "refactor",
    "removes": "refactor",
    "removed": "refactor",
    "delete": "refactor",
    "deletes": "refactor",
    "deleted": "refactor",
    "drop": "refactor",
    "drops": "refactor",
    "dropped": "refactor",
    "rename": "refactor",
    "renames": "refactor",
    "renamed": "refactor",
    "move": "refactor",
    "moves": "refactor",
    "moved": "refactor",
    "migrate": "refactor",
    "migrates": "refactor",
    "migrated": "refactor",
    "refactor": "refactor",
    "refactors": "refactor",
    "refactored": "refactor",
    "replace": "refactor",
    "replaces": "refactor",
    "replaced": "refactor",
    "extract": "refactor",
    "extracts": "refactor",
    "extracted": "refactor",
    # Reverts
    "revert": "revert",
    "reverts": "revert",
    "reverted": "revert",
    # Bug fixes
    "fix": "fix",
    "fixes": "fix",
    "fixed": "fix",
    "fixing": "fix",
    "handle": "fix",
    "handles": "fix",
    "handled": "fix",
    "correct": "fix",
    "corrects": "fix",
    "corrected": "fix",
    "address": "fix",
    "addresses": "fix",
    "addressed": "fix",
    "addressing": "fix",
    # Dependency / tooling bumps
    "bump": "chore",
    "bumps": "chore",
    "bumped": "chore",
    "upgrade": "chore",
    "upgrades": "chore",
    "upgraded": "chore",
    # Access / permissions management
    "grant": "chore",
    "grants": "chore",
    "granted": "chore",
    # Credential / secret rotation
    "rotate": "chore",
    "rotates": "chore",
    "rotated": "chore",
}

# Compound patterns for Renovate/Dependabot-style dependency updates.
DEPENDENCY_BUMP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(update|bump)\s+dependency\s+\S+", re.IGNORECASE),
    re.compile(r"^(update|bump)\s+\S+\s+to\s+v?\d", re.IGNORECASE),
    re.compile(
        r"^(chore|fix|build)(\([^)]*\))?:\s*update\s+dependency\s+\S+",
        re.IGNORECASE,
    ),
]


def match_conventional(subject: str) -> tuple[str, float] | None:
    m = _VERB_PATTERN.match(subject)
    if m:
        return (m.group(1).lower(), 1.0)
    return None


def match_first_verb(subject: str) -> tuple[str, float] | None:
    tokens = subject.split()
    first = tokens[0].lower() if tokens else ""
    verb = FIRST_VERB_RULES.get(first)
    if verb:
        return (verb, 1.0)
    return None


def match_dependency_bump(subject: str) -> tuple[str, float] | None:
    for pattern in DEPENDENCY_BUMP_PATTERNS:
        if pattern.match(subject):
            return ("chore", 1.0)
    return None


def classify_commit(subject: str, body: str | None = None) -> tuple[str, float]:
    conv = match_conventional(subject)
    if conv:
        return conv
    first_verb = match_first_verb(subject)
    if first_verb:
        return first_verb
    dep = match_dependency_bump(subject)
    if dep:
        return dep
    return ("unclear", 0.0)
