import json
import tempfile
from pathlib import Path
from string import Template

_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "almanac.html"
_TEMPLATE = Template(_TEMPLATE_PATH.read_text(encoding="utf-8"))


def _safe_json(bundle: dict) -> str:
    # Escape sequences that would let string content break out of the
    # enclosing <script> element or confuse a JS parser. `JSON.parse`
    # accepts `<\/` unchanged.
    raw = json.dumps(bundle, ensure_ascii=False)
    return (
        raw.replace("</", "<\\/")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_html(bundle: dict) -> str:
    return _TEMPLATE.safe_substitute(BUNDLE_JSON=_safe_json(bundle))


def _safe_slug(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in s)


def write_html(bundle: dict, path: Path | None = None) -> Path:
    if path is not None:
        out_path = Path(path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(render_html(bundle), encoding="utf-8")
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
        f.write(render_html(bundle))
        return Path(f.name)
