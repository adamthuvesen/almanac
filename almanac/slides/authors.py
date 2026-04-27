"""Authors slide: top 10 by commit count with lines added/removed."""

from __future__ import annotations

from almanac.slides._util import (
    assemble,
    center,
    emphasize,
    microcopy_line,
    paint,
    sanitize_tty,
)


class _Authors:
    name = "authors"
    requires = frozenset({"authors"})

    def __call__(self, bundle: dict, width: int, height: int) -> str:
        authors = bundle.get("authors", [])
        lines = ["" for _ in range(height)]
        if height >= 2:
            lines[1] = center(emphasize("Authors", "rust"), width)

        shown = authors[:10]
        omitted = max(0, len(authors) - len(shown))
        start = 3

        name_w = min(32, max(12, width // 3))
        header = (
            f"  {paint('#'.rjust(3), 'olive')}  {paint('author'.ljust(name_w), 'olive')}"
            f"  {paint('commits'.rjust(8), 'olive')}"
            f"  {paint('+added'.rjust(10), 'olive')}"
            f"  {paint('-removed'.rjust(10), 'olive')}"
        )
        if height > start:
            lines[start] = header

        for i, a in enumerate(shown):
            row_idx = start + 1 + i
            if row_idx >= height - 1:
                break
            name = sanitize_tty(a.get("name", "?"))
            if len(name) > name_w:
                name = name[: name_w - 1] + "…"
            commits = a.get("commits", 0)
            added = a.get("lines_added", 0)
            removed = a.get("lines_removed", 0)
            row = (
                f"  {paint(str(i + 1).rjust(3), 'plum')}  "
                f"{paint(name.ljust(name_w), 'ink')}  "
                f"{paint(str(commits).rjust(8), 'sky')}  "
                f"{paint(f'+{added}'.rjust(10), 'olive')}  "
                f"{paint(f'-{removed}'.rjust(10), 'rust')}"
            )
            lines[row_idx] = row

        if omitted:
            footer = paint(f"…and {omitted} more", "olive")
            lines[min(height - 2, start + 1 + len(shown) + 1)] = "  " + footer
        signoff = microcopy_line(bundle, "closer_signoff", "plum")
        if signoff and height >= 2:
            lines[height - 1] = center(signoff, width)
        return assemble(lines, width, height)


slide = _Authors()
