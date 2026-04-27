"""Top Files slide: horizontal bar chart of files_by_churn (edit counts)."""

from __future__ import annotations

from almanac.renderer.ansi import hbar
from almanac.slides._util import (
    assemble,
    center,
    emphasize,
    microcopy_line,
    paint,
    rule,
    sanitize_tty,
    subdued,
)


class _TopFiles:
    name = "top_files"
    requires = frozenset({"files_by_churn"})

    def __call__(self, bundle: dict, width: int, height: int) -> str:
        files = bundle.get("files_by_churn", [])
        lines = ["" for _ in range(height)]
        if height >= 2:
            lines[1] = center(emphasize("Top Files by Churn", "rust"), width)
        cap = microcopy_line(bundle, "top_files_caption", "olive")
        if cap and height >= 3:
            lines[2] = center(cap, width)
        if height >= 4:
            lines[3] = rule(width)

        start = 4
        available = max(0, height - start - 2)
        shown = files[:available]
        omitted = max(0, len(files) - len(shown))

        if not shown:
            return assemble(lines, width, height)

        rank_w = 4  # "  #1" — right-justified rank prefix
        path_w = min(40, max(12, width // 3))
        count_w = 6
        bar_w = max(6, width - rank_w - path_w - count_w - 5)
        max_edits = max(f["edits"] for f in shown)

        for i, f in enumerate(shown):
            path = sanitize_tty(f["path"])
            if len(path) > path_w:
                path = "…" + path[-(path_w - 1) :]
            path = path.ljust(path_w)
            edits = f["edits"]
            bar = hbar(edits, max_edits, bar_w)
            rank = subdued(f"#{i + 1}".rjust(rank_w))
            row = (
                f"{rank}  {paint(path, 'ink')}  "
                f"{paint(bar, 'sky')} {paint(str(edits).rjust(count_w), 'plum')}"
            )
            lines[start + i] = row

        if omitted:
            footer = paint(f"…and {omitted} more", "olive")
            lines[min(height - 2, start + len(shown) + 1)] = "  " + footer
        return assemble(lines, width, height)


slide = _TopFiles()
