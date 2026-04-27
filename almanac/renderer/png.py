"""1200×630 share card as PNG (Playwright; optional almanac[png] extra)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from string import Template

import click

from almanac.renderer.html import _safe_json

_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "card.html"
_CARD_TEMPLATE = Template(_TEMPLATE_PATH.read_text(encoding="utf-8"))


def _refuse_symlink_out_path(path: Path) -> None:
    p = Path(path)
    if p.exists() and p.is_symlink():
        raise click.ClickException(
            f"refusing to write PNG: {path} exists and is a symlink"
        )


def build_card_html(bundle: dict) -> str:
    """Return self-contained card HTML (template + escaped bundle JSON)."""
    return _CARD_TEMPLATE.safe_substitute(BUNDLE_JSON=_safe_json(bundle))


def render_png(bundle: dict, out_path: Path) -> None:
    """Render ``bundle`` to a 1200×630 PNG at ``out_path`` using headless Chromium."""
    from playwright.sync_api import sync_playwright

    out = Path(out_path)
    _refuse_symlink_out_path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    html = build_card_html(bundle)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".html",
        delete=False,
    ) as f:
        f.write(html)
        tmp_path = f.name
    try:
        uri = Path(tmp_path).as_uri()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(
                viewport={"width": 1200, "height": 630},
                device_scale_factor=2,
            )
            page = context.new_page()
            page.goto(uri, wait_until="load")
            page.screenshot(
                path=str(out),
                full_page=False,
                type="png",
                scale="css",
            )
            context.close()
            browser.close()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
