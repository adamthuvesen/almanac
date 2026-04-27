"""Year in Numbers slide: six key metrics in a 2×3 grid."""

from __future__ import annotations

from almanac.slides._util import assemble, center, emphasize, microcopy_line, paint


def _fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n / 1000:.0f}K"
    if n >= 1_000:
        return f"{n / 1000:.1f}K"
    return str(n)


def _cell(label: str, value: str, col_w: int) -> tuple[str, str]:
    return (
        center(paint(label, "plum"), col_w),
        center(emphasize(value, "sky"), col_w),
    )


class _Numbers:
    name = "numbers"
    requires = frozenset({"commit_count"})

    def __call__(self, bundle: dict, width: int, height: int) -> str:
        biggest = bundle.get("biggest_commit") or {}
        metrics = [
            ("COMMITS", _fmt(bundle.get("commit_count", 0))),
            ("LINES ADDED", _fmt(bundle.get("lines_added", 0))),
            ("LINES REMOVED", _fmt(bundle.get("lines_removed", 0))),
            ("LONGEST STREAK", f"{bundle.get('longest_streak_days', 0)} days"),
            ("LONGEST GAP", f"{bundle.get('longest_gap_days', 0)} days"),
            ("BIGGEST COMMIT", _fmt(biggest.get("delta", 0))),
        ]

        lines = ["" for _ in range(height)]
        if height >= 2:
            lines[1] = center(emphasize("Year in Numbers", "rust"), width)
        cap = microcopy_line(bundle, "numbers_caption", "olive")
        if cap and height >= 3:
            lines[2] = center(cap, width)

        col_w = width // 3
        # Keep the grid visually compact even on tall terminals.
        row_h = min(6, max(3, (height - 4) // 2))
        start_row = max(3, (height - (row_h * 2 + 2)) // 2)

        for row_idx in range(2):
            row_cells = metrics[row_idx * 3 : row_idx * 3 + 3]
            label_parts = []
            value_parts = []
            for label, value in row_cells:
                lbl, val = _cell(label, value, col_w)
                label_parts.append(lbl)
                value_parts.append(val)
            r = start_row + row_idx * row_h
            if r < height:
                lines[r] = "".join(label_parts)
            if r + 1 < height:
                lines[r + 1] = "".join(value_parts)
        return assemble(lines, width, height)


slide = _Numbers()
