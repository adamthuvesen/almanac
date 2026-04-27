"""Commit Verbs slide: proportional bar + legend."""

from __future__ import annotations

from almanac.renderer import ansi
from almanac.slides._util import (
    assemble,
    center,
    emphasize,
    microcopy_line,
    paint,
    stacked_bar,
)

_VERB_COLORS = {
    "feat": "sky",
    "fix": "rust",
    "chore": "olive",
    "docs": "plum",
    "refactor": "ink",
    "test": "cream",
    "style": "olive",
    "perf": "sky",
    "build": "plum",
    "ci": "ink",
    "revert": "rust",
    "unclear": "mist",
}


class _Verbs:
    name = "verbs"
    requires = frozenset({"verbs", "commit_count"})

    def __call__(self, bundle: dict, width: int, height: int) -> str:
        verbs = bundle.get("verbs", {})
        total = bundle.get("commit_count", 0)
        lines = ["" for _ in range(height)]
        if height >= 2:
            lines[1] = center(emphasize("Commit Verbs", "rust"), width)
        cap = microcopy_line(bundle, "verbs_caption", "olive")
        if cap and height >= 3:
            lines[2] = center(cap, width)

        if total <= 0:
            return assemble(lines, width, height)

        # Sort by count desc, drop zero counts
        ranked = sorted(
            [(k, v) for k, v in verbs.items() if v > 0],
            key=lambda kv: -kv[1],
        )
        if not ranked:
            return assemble(lines, width, height)

        bar_w = max(10, width - 4)
        parts = [
            (count / total, _VERB_COLORS.get(verb, "olive")) for verb, count in ranked
        ]
        if height >= 4:
            lines[3] = "  " + stacked_bar(parts, bar_w)

        start = 5
        available = max(0, height - start - 1)
        for i, (verb, count) in enumerate(ranked[:available]):
            share = count / total
            color = _VERB_COLORS.get(verb, "olive")
            marker = ansi.truecolor(*ansi.PALETTE[color]) + "█" + ansi.reset()
            row = f"  {marker} {paint(verb.ljust(10), 'ink')} {count:>5}  {paint(f'{share * 100:>5.1f}%', 'plum')}"
            lines[start + i] = row
        return assemble(lines, width, height)


slide = _Verbs()
