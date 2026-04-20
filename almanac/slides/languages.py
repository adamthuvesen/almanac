"""Languages slide: proportional bar + ranked list with share %."""

from __future__ import annotations

from almanac.renderer import ansi
from almanac.slides._util import (
    assemble,
    center,
    emphasize,
    paint,
    sanitize_tty,
    stacked_bar,
)

_SEG_COLORS = ["rust", "olive", "sky", "plum", "ink", "cream"]


class _Languages:
    name = "languages"
    requires = frozenset({"languages"})

    def __call__(self, bundle: dict, width: int, height: int) -> str:
        langs = bundle.get("languages", [])
        lines = ["" for _ in range(height)]
        if height >= 2:
            lines[1] = center(emphasize("Languages", "rust"), width)

        if not langs:
            return assemble(lines, width, height)

        total_lines = sum(max(0, lang.get("lines", 0)) for lang in langs)
        bar_w = max(10, width - 4)
        visible = [lang for lang in langs if lang.get("lines", 0) > 0]
        parts = [
            (
                lang.get("lines", 0) / total_lines if total_lines else 0,
                _SEG_COLORS[i % len(_SEG_COLORS)],
            )
            for i, lang in enumerate(visible)
        ]
        if height >= 4:
            lines[3] = "  " + stacked_bar(parts, bar_w)

        start = 5
        available = max(0, height - start - 1)
        shown = visible[:available]
        for i, lang in enumerate(shown):
            share = lang.get("lines", 0) / total_lines if total_lines else 0
            color = _SEG_COLORS[i % len(_SEG_COLORS)]
            ext = sanitize_tty(lang.get("ext") or "(none)")
            ext_str = ext.ljust(10)
            lines_str = f"{lang.get('lines', 0):>8} lines"
            share_str = f"{share * 100:>5.1f}%"
            marker = ansi.truecolor(*ansi.PALETTE[color]) + "█" + ansi.reset()
            lines[start + i] = (
                f"  {marker} {paint(ext_str, 'ink')} {lines_str}  {paint(share_str, 'plum')}"
            )
        return assemble(lines, width, height)


slide = _Languages()
