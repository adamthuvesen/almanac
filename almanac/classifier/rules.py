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

# Base verb → CC type. Add one line here to cover a new verb family.
_BASE_VERBS: dict[str, str] = {
    # New capability
    "add":       "feat",
    "introduce": "feat",
    "implement": "feat",
    "create":    "feat",
    "extend":    "feat",
    # Restructuring / moving code
    "remove":    "refactor",
    "delete":    "refactor",
    "drop":      "refactor",
    "rename":    "refactor",
    "move":      "refactor",
    "migrate":   "refactor",
    "refactor":  "refactor",
    "replace":   "refactor",
    "extract":   "refactor",
    # Reverts
    "revert":    "revert",
    # Bug fixes
    "fix":       "fix",
    "handle":    "fix",
    "correct":   "fix",
    "address":   "fix",
    # Dependency / tooling bumps
    "bump":      "chore",
    "upgrade":   "chore",
    # Access / permissions management
    "grant":     "chore",
    # Credential / secret rotation
    "rotate":    "chore",
}

# Verbs whose final consonant doubles before -ed/-ing (e.g. drop → dropped).
_CVC_DOUBLE: frozenset[str] = frozenset({"drop"})


def _inflect(verb: str) -> list[str]:
    """Return [base, 3ps, past, gerund] for a regular English verb."""
    if verb.endswith("e"):                        # create → creates, created, creating
        return [verb, verb + "s", verb + "d", verb[:-1] + "ing"]
    if re.search(r"(x|sh|ch|ss)$", verb):         # fix → fixes; address → addresses
        return [verb, verb + "es", verb + "ed", verb + "ing"]
    if verb in _CVC_DOUBLE:                       # drop → dropped, dropping
        return [verb, verb + "s", verb + verb[-1] + "ed", verb + verb[-1] + "ing"]
    return [verb, verb + "s", verb + "ed", verb + "ing"]


# First-token → CC type, auto-generated from _BASE_VERBS.
FIRST_VERB_RULES: dict[str, str] = {
    form: cc_type
    for base, cc_type in _BASE_VERBS.items()
    for form in _inflect(base)
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
