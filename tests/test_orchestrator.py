from __future__ import annotations

import os
import pty
import threading
import time
import tty

from almanac.renderer.orchestrator import _read_key
from almanac.renderer.slide import filter_slides


class _FakeSlide:
    def __init__(self, name: str, requires: frozenset[str]):
        self.name = name
        self.requires = requires

    def __call__(self, bundle, width, height):
        return f"[{self.name}]"


def test_filter_slides_keeps_satisfied():
    slides = [
        _FakeSlide("cover", frozenset()),
        _FakeSlide("authors", frozenset({"authors"})),
    ]
    bundle = {"authors": [{"name": "a"}]}
    kept = filter_slides(slides, bundle)
    assert [s.name for s in kept] == ["cover", "authors"]


def test_filter_slides_drops_when_empty_list():
    slides = [
        _FakeSlide("cover", frozenset()),
        _FakeSlide("authors", frozenset({"authors"})),
    ]
    bundle = {"authors": []}
    kept = filter_slides(slides, bundle)
    assert [s.name for s in kept] == ["cover"]


def test_filter_slides_drops_when_key_missing():
    slides = [_FakeSlide("authors", frozenset({"authors"}))]
    kept = filter_slides(slides, {})
    assert kept == []


def test_filter_slides_populated_bundle_keeps_all():
    from almanac.slides import SLIDES

    bundle = {
        "commit_count": 10,
        "by_dow": [1] * 7,
        "by_hour": [1] * 24,
        "files_by_churn": [{"path": "a", "edits": 1, "lines": 1}],
        "languages": [{"ext": ".py", "lines": 10, "share": 1.0}],
        "verbs": {"feat": 10},
        "authors": [{"name": "a", "commits": 1, "lines_added": 1, "lines_removed": 0}],
    }
    kept = filter_slides(SLIDES, bundle)
    assert len(kept) == len(SLIDES)


def test_filter_slides_sparse_bundle_drops_authors():
    from almanac.slides import SLIDES

    bundle = {
        "commit_count": 10,
        "by_dow": [1] * 7,
        "by_hour": [1] * 24,
        "files_by_churn": [{"path": "a", "edits": 1, "lines": 1}],
        "languages": [{"ext": ".py", "lines": 10, "share": 1.0}],
        "verbs": {"feat": 10},
        "authors": [],  # empty → dropped
    }
    kept_names = [s.name for s in filter_slides(SLIDES, bundle)]
    assert "authors" not in kept_names


def test_read_key_returns_esc_without_blocking():
    master_fd, slave_fd = pty.openpty()
    result: dict[str, str] = {}
    try:
        tty.setraw(slave_fd)

        def read():
            result["key"] = _read_key(slave_fd)

        thread = threading.Thread(target=read)
        thread.start()
        os.write(master_fd, b"\x1b")
        thread.join(0.2)

        assert not thread.is_alive()
        assert result["key"] == "esc"
    finally:
        os.close(master_fd)
        os.close(slave_fd)


def test_read_key_keeps_arrow_navigation():
    master_fd, slave_fd = pty.openpty()
    result: dict[str, str] = {}
    try:
        tty.setraw(slave_fd)

        def read():
            result["key"] = _read_key(slave_fd)

        thread = threading.Thread(target=read)
        thread.start()
        time.sleep(0.01)
        os.write(master_fd, b"\x1b[C")
        thread.join(0.2)

        assert not thread.is_alive()
        assert result["key"] == "right"
    finally:
        os.close(master_fd)
        os.close(slave_fd)
