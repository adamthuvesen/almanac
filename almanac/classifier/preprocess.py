"""Subject preprocessing — strips noise before classification."""

from __future__ import annotations

import re

from almanac.classifier.rules import FIRST_VERB_RULES, VERB_PREFIXES

_CONV_VERB_SET: frozenset[str] = frozenset(v.lower() for v in VERB_PREFIXES)
# Tokens that should never be mistaken for a ticket/branch prefix.
_PROTECTED_TOKENS: frozenset[str] = _CONV_VERB_SET | frozenset(FIRST_VERB_RULES.keys())

# Trailing PR-number suffix: " (#1234)"
_PR_SUFFIX = re.compile(r"\s*\(#\d+\)\s*$")

# Leading bracketed ticket prefix: "[ABC-123] " or "[JIRA-42] "
_BRACKETED_TICKET = re.compile(r"^\[[A-Z]+-\d+\]\s*")

# Leading bare ticket prefix: "ABC-123 ", "PROJ 821", or "JIRA-1914: ".
# Accepts whitespace OR colon+whitespace as the separator after the digits.
# Do not strip if the alpha token is a Conventional Commits type or first-verb rule word.
_BARE_TICKET = re.compile(r"^([A-Za-z]{2,6})\s*[-\s]\d+[:\s]\s*(?=\S)")

# Branch-name prefix: "slug/" where slug is 1–20 alphanumeric/hyphen/underscore chars
# and is NOT a Conventional Commits verb token.
_BRANCH_SLUG = re.compile(r"^([A-Za-z0-9_-]{1,20})/(.+)$")

# CC colon-without-space normaliser: "fix:message" → "fix: message".
# Matches a CC verb (with optional breaking-change ! and optional scope) followed
# immediately by a colon and a non-whitespace character.
_CC_VERB_ALTS = "|".join(VERB_PREFIXES)
_CC_COLON_NO_SPACE = re.compile(
    r"^(?:" + _CC_VERB_ALTS + r")\s*!?(?:\([^)]*\))?:(?=[^\s])",
    re.IGNORECASE,
)


def preprocess(subject: str) -> str:
    """Strip universal noise from a commit subject before classification."""
    s = _PR_SUFFIX.sub("", subject).strip()
    s = _BRACKETED_TICKET.sub("", s).strip()

    # Strip branch-slug prefix first; this may reveal a bare ticket underneath.
    m = _BRANCH_SLUG.match(s)
    if m:
        slug = m.group(1)
        if slug.lower() not in _CONV_VERB_SET:
            s = m.group(2).strip()

    # Strip bare ticket prefix (case-insensitive, but not a verb token).
    m = _BARE_TICKET.match(s)
    if m and m.group(1).lower() not in _PROTECTED_TOKENS:
        s = s[m.end() :].strip()

    # Normalise CC colon-without-space so the CC regex can match it.
    # "fix:give permission" → "fix: give permission"
    if _CC_COLON_NO_SPACE.match(s):
        colon_pos = s.index(":")
        s = s[: colon_pos + 1] + " " + s[colon_pos + 1 :]

    return s
