"""Alt-screen presentation loop: render slides, read keypresses, restore."""

from __future__ import annotations

import os
import select
import signal
import sys
import termios
import tty
from collections.abc import Iterable

from almanac.renderer import ansi
from almanac.renderer.slide import Slide, filter_slides


def _read_key(stdin_fd: int) -> str:
    """Read one logical keypress in raw mode. Returns a short identifier."""
    b = os.read(stdin_fd, 1)
    if b == b"\x1b":  # ESC — might start a CSI escape
        # Only peek for CSI bytes that are already available so a lone ESC
        # remains responsive in raw mode.
        ready, _, _ = select.select([stdin_fd], [], [], 0)
        if not ready:
            return "esc"
        b2 = os.read(stdin_fd, 1)
        ready, _, _ = select.select([stdin_fd], [], [], 0)
        if not ready:
            return "esc"
        b3 = os.read(stdin_fd, 1)
        seq = b + b2 + b3
        if seq == b"\x1b[C":
            return "right"
        if seq == b"\x1b[D":
            return "left"
        return "esc"
    if b == b" ":
        return "right"
    if b in (b"q", b"Q"):
        return "quit"
    if b == b"\x03":  # Ctrl-C
        return "quit"
    if b == b"\r" or b == b"\n":
        return "right"
    return ""


def _footer(idx: int, total: int, width: int) -> str:
    label = f"{idx + 1} / {total}  ·  ← → to navigate  ·  q to quit"
    pad = max(0, width - len(label))
    return " " * (pad // 2) + label


def run_presentation(
    slides: Iterable[Slide],
    bundle: dict,
    term_size: tuple[int, int] | None = None,
) -> None:
    """Present slides on the alt-screen. Blocks until the user quits."""
    ordered = filter_slides(list(slides), bundle)
    if not ordered:
        return

    if term_size is None:
        size = os.get_terminal_size()
        width, height = size.columns, size.lines
    else:
        width, height = term_size

    stdin_fd = sys.stdin.fileno()
    try:
        original_attrs = termios.tcgetattr(stdin_fd)
    except termios.error:
        # Stdin is not a TTY — write alt-screen enter/exit with no interactive
        # loop. This satisfies `almanac --tty > /dev/null` exiting cleanly in
        # redirected/piped environments.
        sys.stdout.write(ansi.enter_alt_screen())
        sys.stdout.write(ansi.exit_alt_screen())
        sys.stdout.flush()
        return
    prev_sigint = signal.getsignal(signal.SIGINT)

    def _restore():
        sys.stdout.write(ansi.exit_alt_screen())
        sys.stdout.write(ansi.reset())
        sys.stdout.flush()
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, original_attrs)

    def _sigint_handler(signum, frame):
        _restore()
        signal.signal(signal.SIGINT, prev_sigint)
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGINT, _sigint_handler)
        tty.setraw(stdin_fd)
        sys.stdout.write(ansi.enter_alt_screen())
        sys.stdout.flush()

        idx = 0
        total = len(ordered)
        while True:
            body = ordered[idx](bundle, width, height - 1)
            footer = _footer(idx, total, width)
            sys.stdout.write(ansi.clear())
            sys.stdout.write(body)
            sys.stdout.write(ansi.move(height, 1))
            sys.stdout.write(ansi.dim() + footer + ansi.reset())
            sys.stdout.flush()

            key = _read_key(stdin_fd)
            if key == "quit":
                break
            if key == "right":
                idx = (idx + 1) % total
            elif key == "left":
                idx = (idx - 1) % total
    finally:
        _restore()
        signal.signal(signal.SIGINT, prev_sigint)
