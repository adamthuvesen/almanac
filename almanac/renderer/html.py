import json
import tempfile
from pathlib import Path
from string import Template

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
_TEMPLATE_PATH = _TEMPLATE_DIR / "almanac.html"
_CSS_PATH = _TEMPLATE_DIR / "almanac.css"
_JS_PATH = _TEMPLATE_DIR / "almanac.js"
_TEMPLATE = Template(_TEMPLATE_PATH.read_text(encoding="utf-8"))
_CSS = _CSS_PATH.read_text(encoding="utf-8")
_JS = _JS_PATH.read_text(encoding="utf-8")
_LINE_SEPARATOR = "\u2028"
_PARAGRAPH_SEPARATOR = "\u2029"


def _safe_json(bundle: dict) -> str:
    # Escape sequences that would let string content break out of the
    # enclosing <script> element or confuse a JS parser. `JSON.parse`
    # accepts `<\/` unchanged.
    raw = json.dumps(bundle, ensure_ascii=False)
    return (
        raw.replace("</", "<\\/")
        .replace(_LINE_SEPARATOR, "\\u2028")
        .replace(_PARAGRAPH_SEPARATOR, "\\u2029")
    )


THEME_CHOICES: tuple[str, ...] = (
    "classic",
    "terminal",
    "midnight",
    "paper",
    "wrapped",
)
VALID_THEMES: frozenset[str] = frozenset(THEME_CHOICES)


def resolve_theme(name: str) -> str:
    key = (name or "").strip().lower()
    if key in VALID_THEMES:
        return key
    raise ValueError(f"theme must be one of: {', '.join(THEME_CHOICES)}")


def _theme_attr(theme: str) -> str:
    return f' data-theme="{resolve_theme(theme)}"'


def render_html(bundle: dict, theme: str = "classic") -> str:
    return _TEMPLATE.safe_substitute(
        ALMANAC_CSS=_CSS,
        ALMANAC_JS=_JS,
        BUNDLE_JSON=_safe_json(bundle),
        THEME_ATTR=_theme_attr(theme),
    )


def _safe_slug(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in s)


def write_html(bundle: dict, path: Path | None = None, theme: str = "classic") -> Path:
    if path is not None:
        out_path = Path(path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_html(bundle, theme=theme), encoding="utf-8")
        return out_path

    label = bundle.get("window", {}).get("label", "window")
    sha = (bundle.get("repo", {}).get("head_sha") or "nohead")[:7]
    name = bundle.get("repo", {}).get("name", "almanac")
    prefix = f"almanac-{_safe_slug(name)}-{_safe_slug(label)}-{sha}-"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=tempfile.gettempdir(),
        prefix=prefix,
        suffix=".html",
        delete=False,
    ) as f:
        f.write(render_html(bundle, theme=theme))
        return Path(f.name)
