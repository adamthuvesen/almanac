"""Top Files slide: horizontal bar chart of files_by_churn (edit counts)."""

from __future__ import annotations

from almanac.renderer.ansi import hbar
from almanac.slides._util import assemble, center, emphasize, paint, sanitize_tty


class _TopFiles:
    name = "top_files"
    requires = frozenset({"files_by_churn"})

    def __call__(self, bundle: dict, width: int, height: int) -> str:
        files = bundle.get("files_by_churn", [])
        lines = ["" for _ in range(height)]
        if height >= 2:
            lines[1] = center(emphasize("Top Files by Churn", "rust"), width)

        start = 3
        available = max(0, height - start - 2)
        shown = files[:available]
        omitted = max(0, len(files) - len(shown))

        if not shown:
            return assemble(lines, width, height)

        path_w = min(40, max(12, width // 3))
        count_w = 6
        bar_w = max(6, width - path_w - count_w - 4)
        max_edits = max(f["edits"] for f in shown) if shown else 0

        for i, f in enumerate(shown):
            path = sanitize_tty(f["path"])
            if len(path) > path_w:
                path = "…" + path[-(path_w - 1) :]
            path = path.ljust(path_w)
            edits = f["edits"]
            bar = hbar(edits, max_edits, bar_w)
            row = f"  {paint(path, 'ink')}  {paint(bar, 'sky')} {paint(str(edits).rjust(count_w), 'plum')}"
            lines[start + i] = row

        if omitted:
            footer = paint(f"…and {omitted} more", "olive")
            lines[min(height - 2, start + len(shown) + 1)] = "  " + footer
        return assemble(lines, width, height)


slide = _TopFiles()
