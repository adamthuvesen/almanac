"""Commit Cadence slide: day-of-week and hour-of-day bar charts side by side."""

from __future__ import annotations

from almanac.renderer.ansi import hbar
from almanac.slides._util import (
    assemble,
    center,
    emphasize,
    ljust,
    microcopy_line,
    paint,
    rule,
    subdued,
)

_DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _bar_color(value: int, max_val: int, on_color: str, off_color: str = "mist") -> str:
    """Return the bar color based on relative intensity."""
    if max_val <= 0 or value <= 0:
        return off_color
    return on_color if value / max_val >= 0.15 else off_color


class _Cadence:
    name = "cadence"
    requires = frozenset({"by_dow", "by_hour"})

    def __call__(self, bundle: dict, width: int, height: int) -> str:
        by_dow = bundle.get("by_dow", [0] * 7)
        by_hour = bundle.get("by_hour", [0] * 24)

        lines = ["" for _ in range(height)]
        if height >= 2:
            lines[1] = center(emphasize("Commit Cadence", "rust"), width)
        cap = microcopy_line(bundle, "cadence_caption", "olive")
        if cap and height >= 3:
            lines[2] = center(cap, width)
        if height >= 4:
            lines[3] = rule(width)
        sub = microcopy_line(bundle, "comeback_caption", "plum") or microcopy_line(
            bundle, "quiet_caption", "plum"
        )

        col_w = width // 2
        bar_w = max(6, col_w - 12)

        dow_max = max(by_dow) if by_dow else 0
        hour_max = max(by_hour) if by_hour else 0

        left_title = subdued("Day of week")
        right_title = subdued("Hour of day")
        if height >= 5:
            lines[4] = ljust("  " + left_title, col_w) + "  " + right_title

        left_rows = []
        for i, count in enumerate(by_dow):
            label = _DOW[i]
            bar = hbar(count, dow_max, bar_w)
            color = _bar_color(count, dow_max, "sky")
            left_rows.append(f"  {label}  {paint(bar, color)} {paint(str(count), color)}")

        right_rows = []
        for hour, count in enumerate(by_hour):
            label = f"{hour:02d}"
            bar = hbar(count, hour_max, bar_w)
            color = _bar_color(count, hour_max, "plum")
            right_rows.append(
                f"  {label}  {paint(bar, color)} {paint(str(count), color)}"
            )

        start = 6
        n_rows = min(len(right_rows), max(0, height - start - 1))
        for i in range(n_rows):
            left = left_rows[i] if i < len(left_rows) else ""
            right = right_rows[i] if i < len(right_rows) else ""
            lines[start + i] = ljust(left, col_w) + right
        if sub and height >= 2:
            lines[height - 1] = center(sub, width)
        return assemble(lines, width, height)


slide = _Cadence()
