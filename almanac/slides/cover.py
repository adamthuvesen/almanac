"""Cover slide: repo name, window label, commit count."""

from __future__ import annotations

from almanac.slides._util import assemble, center, emphasize, microcopy_line, paint


class _Cover:
    name = "cover"
    requires = frozenset()

    def __call__(self, bundle: dict, width: int, height: int) -> str:
        repo_name = bundle.get("repo", {}).get("name", "repository")
        label = bundle.get("window", {}).get("label", "")
        count = bundle.get("commit_count", 0)

        lines = ["" for _ in range(height)]
        mid = height // 2
        if height >= 4:
            lines[max(0, mid - 2)] = center(emphasize(repo_name, "rust"), width)
        if label and height >= 2:
            lines[mid] = center(paint(label, "ink"), width)
        if height >= 3:
            lines[min(height - 1, mid + 2)] = center(
                paint(f"{count} commits", "plum"), width
            )
        intro = microcopy_line(bundle, "cover_intro", "plum")
        if intro and height >= 6:
            lines[min(height - 3, mid + 4)] = center(intro, width)
        if height >= 4:
            lines[height - 2] = center(
                paint("almanac · your codebase, wrapped", "olive"), width
            )
        return assemble(lines, width, height)


slide = _Cover()
