"""Shared helpers for slides: centring, padding."""

from __future__ import annotations

import re

from almanac.renderer import ansi

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# ESC (0x1b), BEL (0x07), and the rest of C0 except \t (0x09) and \n (0x0a),
# plus DEL (0x7f). Strip from any git-sourced string before painting — a
# hostile commit author could otherwise clear the screen, set the terminal
# title via OSC, or emit arbitrary cursor moves during playback.
_TTY_STRIP_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def sanitize_tty(s: str) -> str:
    """Strip ESC/BEL/C0 control bytes (except \\t and \\n) from a string."""
    return _TTY_STRIP_RE.sub("", s)


def visible_len(s: str) -> int:
    return len(_ANSI_RE.sub("", s))


def center(text: str, width: int) -> str:
    """Centre text within `width`, padding both sides to full width."""
    missing = max(0, width - visible_len(text))
    left = missing // 2
    right = missing - left
    return " " * left + text + " " * right


def ljust(text: str, width: int) -> str:
    pad = max(0, width - visible_len(text))
    return text + " " * pad


def rjust(text: str, width: int) -> str:
    pad = max(0, width - visible_len(text))
    return " " * pad + text


def paint(text: str, color_name: str) -> str:
    return ansi.truecolor(*ansi.PALETTE[color_name]) + text + ansi.reset()


def emphasize(text: str, color_name: str = "rust") -> str:
    return ansi.bold() + ansi.truecolor(*ansi.PALETTE[color_name]) + text + ansi.reset()


def subdued(text: str, color_name: str = "mist") -> str:
    """Dimmed, de-emphasized text — good for labels and secondary info."""
    return ansi.dim() + ansi.truecolor(*ansi.PALETTE[color_name]) + text + ansi.reset()


def rule(width: int, color: str = "mist") -> str:
    """A thin centered horizontal rule for visual section breaks."""
    inner = "─" * min(width - 4, 52)
    line = ansi.dim() + ansi.truecolor(*ansi.PALETTE[color]) + inner + ansi.reset()
    return center(line, width)


def microcopy_line(bundle: dict, slot: str, color: str = "olive") -> str | None:
    """Return a sanitized, painted caption from ``bundle.microcopy[slot]``.

    Returns ``None`` when the slot is missing, ``None``, or empty so the
    caller can leave its layout untouched (no blank line in place of a
    missing caption).
    """
    text = (bundle.get("microcopy") or {}).get(slot)
    if not text:
        return None
    return paint(sanitize_tty(text), color)


def assemble(lines: list[str], width: int, height: int) -> str:
    """Clip to height, join with \\n. Caller is responsible for widths."""
    out = [lines[i] if i < len(lines) else "" for i in range(height)]
    return "\r\n".join(out)


def stacked_bar(
    parts: list[tuple[float, str]],
    bar_w: int,
) -> str:
    """Paint a proportional stacked bar of width `bar_w`.

    `parts` is a list of `(share, color_name)` tuples where shares are
    expected to sum to roughly 1.0. The last segment absorbs any
    rounding remainder so the bar is always exactly `bar_w` wide
    (excluding ANSI escapes).
    """
    segments: list[str] = []
    consumed = 0
    last = len(parts) - 1
    for i, (share, color) in enumerate(parts):
        seg_len = bar_w - consumed if i == last else max(1, round(share * bar_w))
        seg_len = min(seg_len, bar_w - consumed)
        if seg_len <= 0:
            continue
        segments.append(paint("█" * seg_len, color))
        consumed += seg_len
        if consumed >= bar_w:
            break
    return "".join(segments)
