"""ANSI primitives for the almanac TTY renderer.

Stdlib-only. No curses, no blessed. Emits escape sequences directly.
Truecolor is used when `$COLORTERM` indicates support; otherwise the
closest 256-colour approximation is emitted.
"""

from __future__ import annotations

import os

ESC = "\x1b["

# Palette: six named colours, RGB tuples. Baked-in "almanac" theme.
PALETTE: dict[str, tuple[int, int, int]] = {
    "ink": (34, 34, 40),
    "cream": (247, 241, 227),
    "rust": (192, 86, 60),
    "olive": (138, 142, 72),
    "sky": (98, 143, 176),
    "plum": (130, 90, 130),
    "mist": (140, 135, 128),
}


_TRUECOLOR: bool | None = None


def _supports_truecolor() -> bool:
    global _TRUECOLOR
    if _TRUECOLOR is None:
        _TRUECOLOR = os.environ.get("COLORTERM", "").lower() in {"truecolor", "24bit"}
    return _TRUECOLOR


def _rgb_to_256(r: int, g: int, b: int) -> int:
    """Approximate an RGB triple to the 256-colour xterm cube index."""
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return 232 + round((r - 8) / 247 * 24)
    return 16 + 36 * round(r / 255 * 5) + 6 * round(g / 255 * 5) + round(b / 255 * 5)


def truecolor(r: int, g: int, b: int, *, bg: bool = False) -> str:
    """Return a foreground (or background) colour SGR sequence.

    Falls back to 256-colour when `$COLORTERM` doesn't indicate truecolor.
    """
    prefix = "48" if bg else "38"
    if _supports_truecolor():
        return f"{ESC}{prefix};2;{r};{g};{b}m"
    return f"{ESC}{prefix};5;{_rgb_to_256(r, g, b)}m"


def color256(n: int, *, bg: bool = False) -> str:
    prefix = "48" if bg else "38"
    return f"{ESC}{prefix};5;{n}m"


def reset() -> str:
    return f"{ESC}0m"


def bold() -> str:
    return f"{ESC}1m"


def dim() -> str:
    return f"{ESC}2m"


def enter_alt_screen() -> str:
    # alt-screen on + hide cursor
    return f"{ESC}?1049h{ESC}?25l"


def exit_alt_screen() -> str:
    # show cursor + alt-screen off
    return f"{ESC}?25h{ESC}?1049l"


def clear() -> str:
    return f"{ESC}2J{ESC}H"


def move(row: int, col: int) -> str:
    # 1-based like the ANSI spec
    return f"{ESC}{row};{col}H"


_BLOCKS = " ▏▎▍▌▋▊▉█"
_SPARK = " ▁▂▃▄▅▆▇█"


def hbar(value: float, max_val: float, width: int) -> str:
    """A horizontal bar using Unicode eighth-blocks for fractional width."""
    if width <= 0:
        return ""
    if max_val <= 0 or value <= 0:
        return " " * width
    ratio = min(1.0, value / max_val)
    eighths = int(round(ratio * width * 8))
    full = eighths // 8
    remainder = eighths % 8
    bar = "█" * full
    if remainder and full < width:
        bar += _BLOCKS[remainder]
    return bar.ljust(width)


def sparkline(values: list[float] | list[int], width: int) -> str:
    """Compact bar chart using Braille/block ramps. `width` ignored if len(values) fits."""
    if not values or width <= 0:
        return ""
    peak = max(values)
    if peak <= 0:
        return _SPARK[0] * min(len(values), width)
    # Sample/compress values to fit width.
    n = len(values)
    if n > width:
        step = n / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = list(values)
    out = []
    for v in sampled:
        idx = int(round(v / peak * (len(_SPARK) - 1)))
        out.append(_SPARK[idx])
    return "".join(out)


def box(title: str, content: str, width: int, height: int) -> str:
    """Light box-drawing border with a title. Content is lines joined by \\n.

    Returns a string with embedded newlines — caller positions it.
    """
    if width < 4 or height < 2:
        return content
    top = "╭─ " + title + " " + "─" * max(0, width - 5 - len(title)) + "╮"
    top = top[:width]
    bottom = "╰" + "─" * (width - 2) + "╯"
    lines = content.splitlines()
    body = []
    inner_w = width - 2
    for i in range(height - 2):
        # NB: caller is responsible for passing plain-text lines; ANSI in
        # `line` would skew the ljust width calculation here.
        line = lines[i] if i < len(lines) else ""
        body.append("│" + line.ljust(inner_w)[:inner_w] + "│")
    return "\n".join([top, *body, bottom])
