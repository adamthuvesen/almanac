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
    "add": "feat",
    "introduce": "feat",
    "implement": "feat",
    "create": "feat",
    "extend": "feat",
    "enrich": "feat",
    # Restructuring / moving code — includes expanded vocabulary
    # (update, change, propagate, ...) that defaults to refactor.
    # Specific high-signal second words get rescued by _BIGRAM_OVERRIDES.
    "remove": "refactor",
    "delete": "refactor",
    "drop": "refactor",
    "rename": "refactor",
    "move": "refactor",
    "migrate": "refactor",
    "refactor": "refactor",
    "replace": "refactor",
    "extract": "refactor",
    "update": "refactor",
    "change": "refactor",
    "propagate": "refactor",
    "align": "refactor",
    "simplify": "refactor",
    "cluster": "refactor",
    "set": "refactor",
    "keep": "refactor",
    "default": "refactor",
    "allow": "refactor",
    "apply": "refactor",
    "nullify": "refactor",
    "cast": "refactor",
    "exclude": "refactor",
    "provide": "refactor",
    "use": "refactor",
    "lower": "refactor",
    "adjust": "refactor",
    "sort": "refactor",
    "repoint": "refactor",
    "readd": "refactor",
    "reupload": "refactor",
    "dedupe": "refactor",
    "deduplicate": "refactor",
    "merge": "refactor",
    "tidy": "refactor",
    "reclassify": "refactor",
    "enable": "refactor",
    "disable": "refactor",
    "refine": "refactor",
    "rework": "refactor",
    "improve": "refactor",
    # Reverts
    "revert": "revert",
    # Bug fixes
    "fix": "fix",
    "handle": "fix",
    "correct": "fix",
    "address": "fix",
    # Tests
    "test": "test",
    # Docs
    "docs": "docs",
    "document": "docs",
    "documentation": "docs",
    # Style / formatting
    "style": "style",
    "format": "style",
    "lint": "style",
    # Performance
    "perf": "perf",
    "optimize": "perf",
    # Build
    "build": "build",
    "package": "build",
    # Dependency / tooling bumps
    "bump": "chore",
    "upgrade": "chore",
    # Access / permissions management
    "grant": "chore",
    # Credential / secret rotation
    "rotate": "chore",
}

# Verbs whose final consonant doubles before -ed/-ing (e.g. drop → dropped).
_CVC_DOUBLE: frozenset[str] = frozenset({"drop", "set"})


def _inflect(verb: str) -> list[str]:
    """Return [base, 3ps, past, gerund] for a regular English verb."""
    if verb.endswith("e"):  # create → creates, created, creating
        return [verb, verb + "s", verb + "d", verb[:-1] + "ing"]
    if re.search(r"(x|sh|ch|ss)$", verb):  # fix → fixes; address → addresses
        return [verb, verb + "es", verb + "ed", verb + "ing"]
    if verb in _CVC_DOUBLE:  # drop → dropped, dropping
        return [verb, verb + "s", verb + verb[-1] + "ed", verb + verb[-1] + "ing"]
    return [verb, verb + "s", verb + "ed", verb + "ing"]


# First-token → CC type, auto-generated from _BASE_VERBS.
FIRST_VERB_RULES: dict[str, str] = {
    form: cc_type for base, cc_type in _BASE_VERBS.items() for form in _inflect(base)
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

# (first_word, second_word) bigram overrides — consulted before the
# first-verb table so multi-class leading verbs (`update`, `change`, ...)
# can be rescued from their default mapping when the object noun carries
# a strong signal. Cap at ~25 entries; each entry should exist because a
# real commit subject demanded it.
_BIGRAM_OVERRIDES: dict[tuple[str, str], str] = {
    # Docs rescues
    ("update", "readme"): "docs",
    ("update", "doc"): "docs",
    ("update", "docs"): "docs",
    ("update", "documentation"): "docs",
    ("change", "readme"): "docs",
    # Dependency/package rescues
    ("update", "dependency"): "chore",
    ("update", "deps"): "chore",
    ("update", "lock"): "chore",
    ("update", "lockfile"): "chore",
    ("update", "package"): "chore",
    ("update", "packages"): "chore",
    ("update", "version"): "chore",
    ("bump", "dependency"): "chore",
    ("pin", "dependency"): "chore",
    # Performance rescues
    ("update", "performance"): "perf",
    ("change", "performance"): "perf",
    ("improve", "performance"): "perf",
    ("improve", "query"): "perf",
    ("improve", "speed"): "perf",
    # Test rescues
    ("update", "test"): "test",
    ("update", "tests"): "test",
    ("change", "test"): "test",
    ("change", "severity"): "test",
    ("change", "assertion"): "test",
}


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


def match_bigram_override(subject: str) -> tuple[str, float] | None:
    tokens = subject.split()
    if len(tokens) < 2:
        return None
    key = (tokens[0].lower(), tokens[1].lower())
    verb = _BIGRAM_OVERRIDES.get(key)
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
    bigram = match_bigram_override(subject)
    if bigram:
        return bigram
    first_verb = match_first_verb(subject)
    if first_verb:
        return first_verb
    dep = match_dependency_bump(subject)
    if dep:
        return dep
    return ("unclear", 0.0)
