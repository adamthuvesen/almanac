import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import click
from click.core import ParameterSource

from almanac import __version__
from almanac.ingest import GitLogError, coalesce_identities, iter_commits
from almanac.renderer.html import resolve_theme
from almanac.stats import compute_bundle
from almanac.window import resolve_window

_PNG_INSTALL_HINT = """\
Install almanac[png] to enable PNG export:
  pip install 'almanac[png]'
  playwright install chromium
"""


def _ensure_playwright_for_png() -> None:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        click.echo(_PNG_INSTALL_HINT, err=True)
        raise SystemExit(1)


def _default_png_path(kwargs: dict) -> Path:
    out = kwargs.get("png_out")
    if out:
        return Path(out)
    return Path.cwd() / "summary-card.png"


@click.command()
@click.version_option(__version__, "--version")
@click.option("--repo", type=click.Path(exists=True), default=".", show_default=True)
@click.option("--year", type=int, default=None)
@click.option("--since", default=None, metavar="YYYY-MM-DD")
@click.option("--until", default=None, metavar="YYYY-MM-DD")
@click.option("--author", default=None, help="Exact name or email match")
@click.option("--json", "emit_json", is_flag=True, default=False)
@click.option("--include-merges", is_flag=True, default=False)
@click.option("--debug", is_flag=True, default=False, hidden=True)
@click.option("--tty", is_flag=True, default=False, help="Force the TTY renderer.")
@click.option(
    "--no-tty",
    is_flag=True,
    default=False,
    help="Force the one-line summary, even in a terminal.",
)
@click.option(
    "--html",
    is_flag=True,
    default=False,
    help="Render the HTML presentation and open it in the default browser.",
)
@click.option(
    "--html-out",
    "html_out",
    type=click.Path(),
    default=None,
    help="Write the HTML presentation to PATH (skips browser auto-open).",
)
@click.option(
    "--theme",
    "theme",
    type=str,
    default="classic",
    show_default=True,
    help="HTML report color theme (HTML output only).",
)
@click.option(
    "--png",
    is_flag=True,
    default=False,
    help="Render a 1200×630 PNG share card (requires: pip install 'almanac[png]').",
)
@click.option(
    "--png-out",
    "png_out",
    type=click.Path(),
    default=None,
    metavar="PATH",
    help="Write the PNG to PATH (default: ./summary-card.png in the current directory).",
)
@click.option(
    "--demo",
    is_flag=True,
    default=False,
    help="Use a built-in synthetic repo report (no git or working tree required).",
)
@click.option("--voice", is_flag=True, default=False, help="[not yet implemented]")
@click.option("--soundtrack", is_flag=True, default=False, help="[not yet implemented]")
@click.option("--slides", is_flag=True, default=False, help="[not yet implemented]")
@click.option(
    "--gravatar/--no-gravatar",
    default=False,
    help=(
        "Fetch author avatars from gravatar.com when the HTML report is "
        "opened. Off by default to avoid leaking md5(email) for each author "
        "to a third party."
    ),
)
@click.option(
    "--classifier",
    type=click.Choice(["auto", "rules", "zeroshot"], case_sensitive=False),
    default="auto",
    show_default=True,
    help=(
        "Commit subject classifier: 'auto' picks zero-shot when transformers "
        "is installed (see optional almanac[ml] extra), else regex rules; "
        "'rules' is Conventional Commits only; 'zeroshot' requires "
        "pip install 'almanac[ml]'."
    ),
)
@click.pass_context
def main(ctx, **kwargs):
    """Almanac — Spotify Wrapped for your codebase."""
    try:
        theme = resolve_theme(kwargs["theme"])
    except ValueError as e:
        click.echo(f"Error: {e}.", err=True)
        sys.exit(1)

    is_demo = bool(kwargs.get("demo"))
    if is_demo:
        conflicting: list[str] = []
        for opt in ("repo", "since", "until", "year", "author"):
            if ctx.get_parameter_source(opt) == ParameterSource.COMMANDLINE:
                conflicting.append(f"--{opt.replace('_', '-')}")
        if conflicting:
            flags = ", ".join(conflicting)
            click.echo(
                f"Error: --demo cannot be combined with {flags} (use --demo alone for a "
                "synthetic report).",
                err=True,
            )
            sys.exit(1)

    for flag in [
        "voice",
        "soundtrack",
        "slides",
    ]:
        if kwargs.get(flag):
            click.echo("not yet implemented in this version", err=True)
            sys.exit(1)

    classifier_strategy = kwargs["classifier"]
    if not is_demo and classifier_strategy == "zeroshot":
        from almanac.classifier import has_transformers

        if not has_transformers():
            click.echo(
                "Error: --classifier zeroshot requires optional ML dependencies. "
                "Install with: pip install 'almanac[ml]'",
                err=True,
            )
            sys.exit(1)

    if kwargs.get("png") and not kwargs["emit_json"]:
        _ensure_playwright_for_png()

    if is_demo:
        from almanac.demo import make_demo_bundle

        bundle = make_demo_bundle()
        if kwargs.get("gravatar"):
            for author in bundle["authors"]:
                primary_email = author["emails"][0] if author["emails"] else ""
                if primary_email:
                    normalized = primary_email.strip().lower()
                    author["avatar_hash"] = hashlib.md5(
                        normalized.encode("utf-8")
                    ).hexdigest()

        if kwargs["emit_json"]:
            if kwargs.get("html") or kwargs.get("html_out") or kwargs.get("png"):
                click.echo("note: --json wins, HTML/PNG not generated", err=True)
            click.echo(json.dumps(bundle, ensure_ascii=False))
            return

        want_html = bool(kwargs.get("html"))
        html_out = kwargs.get("html_out")
        want_png = bool(kwargs.get("png"))

        if want_png and not want_html and not html_out:
            from almanac.renderer.png import render_png

            png_path = _default_png_path(kwargs)
            render_png(bundle, png_path)
            click.echo(str(png_path), err=True)
            return

        if is_demo or want_html or html_out:
            if want_html and kwargs.get("tty"):
                click.echo("note: --html wins, TTY not launched", err=True)
            from almanac.renderer.html import write_html

            target = Path(html_out) if html_out else None
            out_path = write_html(bundle, target, theme=theme)
            click.echo(str(out_path), err=True)
            if html_out is None:
                import webbrowser

                webbrowser.open(out_path.as_uri())
            if want_png:
                from almanac.renderer.png import render_png

                png_path = _default_png_path(kwargs)
                render_png(bundle, png_path)
                click.echo(str(png_path), err=True)
            return

        want_tty = kwargs["tty"] or (sys.stdout.isatty() and not kwargs["no_tty"])
        if not want_tty:
            commit_count = bundle["commit_count"]
            fix_count = bundle["verbs"].get("fix", 0)
            fix_pct = round(fix_count / commit_count * 100) if commit_count else 0
            top_file = (
                bundle["files_by_churn"][0]["path"] if bundle["files_by_churn"] else "—"
            )
            click.echo(
                f"{commit_count} commits · {fix_pct}% fix · top file: {top_file}"
            )
            return

        try:
            from almanac.renderer.orchestrator import run_presentation
            from almanac.slides import SLIDES

            try:
                size = os.get_terminal_size()
                term_size = (size.columns, size.lines)
            except OSError:
                term_size = (80, 24)
            run_presentation(SLIDES, bundle, term_size)
        except KeyboardInterrupt:
            pass
        return

    repo = Path(kwargs["repo"]).resolve()

    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--git-dir"],
        capture_output=True,
    )
    if result.returncode != 0:
        click.echo(f"Error: {repo} is not inside a git repository", err=True)
        sys.exit(1)

    try:
        window = resolve_window(
            year=kwargs["year"],
            since=kwargs["since"],
            until=kwargs["until"],
        )
    except (click.UsageError, ValueError) as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    if kwargs["debug"]:
        click.echo(
            f"Window: {window.since} → {window.until} [{window.label}]", err=True
        )

    head_result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    head_sha = head_result.stdout.strip() if head_result.returncode == 0 else ""

    repo_meta = {
        "path": str(repo),
        "name": repo.name,
        "head_sha": head_sha,
    }

    include_merges = kwargs["include_merges"]
    try:
        commits = list(iter_commits(repo, window, include_merges=include_merges))
    except GitLogError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    author_filter = kwargs["author"]
    canonical: dict[str, str] | None = None
    if author_filter:
        canonical = coalesce_identities(commits)
        filter_lc = author_filter.strip().lower()

        def matches_author(c):
            name = canonical.get(c.author_email.lower(), c.author_name)
            return filter_lc in (name.lower(), c.author_email.lower())

        commits = [c for c in commits if matches_author(c)]

    bundle = compute_bundle(
        commits,
        window,
        repo_meta,
        classifier_strategy=classifier_strategy,
        canonical=canonical,
    )

    if kwargs.get("gravatar"):
        for author in bundle["authors"]:
            primary_email = author["emails"][0] if author["emails"] else ""
            if primary_email:
                normalized = primary_email.strip().lower()
                author["avatar_hash"] = hashlib.md5(
                    normalized.encode("utf-8")
                ).hexdigest()

    want_html = bool(kwargs.get("html"))
    html_out = kwargs.get("html_out")

    if kwargs["emit_json"]:
        if want_html or html_out or kwargs.get("png"):
            click.echo("note: --json wins, HTML/PNG not generated", err=True)
        click.echo(json.dumps(bundle, ensure_ascii=False))
        return

    want_png = bool(kwargs.get("png"))

    if want_png and not want_html and not html_out:
        from almanac.renderer.png import render_png

        png_path = _default_png_path(kwargs)
        render_png(bundle, png_path)
        click.echo(str(png_path), err=True)
        return

    if want_html or html_out:
        if want_html and kwargs.get("tty"):
            click.echo("note: --html wins, TTY not launched", err=True)
        from almanac.renderer.html import write_html

        target = Path(html_out) if html_out else None
        out_path = write_html(bundle, target, theme=theme)
        click.echo(str(out_path), err=True)
        if html_out is None:
            import webbrowser

            webbrowser.open(out_path.as_uri())
        if want_png:
            from almanac.renderer.png import render_png

            png_path = _default_png_path(kwargs)
            render_png(bundle, png_path)
            click.echo(str(png_path), err=True)
        return

    want_tty = kwargs["tty"] or (sys.stdout.isatty() and not kwargs["no_tty"])
    if not want_tty:
        commit_count = bundle["commit_count"]
        fix_count = bundle["verbs"].get("fix", 0)
        fix_pct = round(fix_count / commit_count * 100) if commit_count else 0
        top_file = (
            bundle["files_by_churn"][0]["path"] if bundle["files_by_churn"] else "—"
        )
        click.echo(f"{commit_count} commits · {fix_pct}% fix · top file: {top_file}")
        return

    try:
        from almanac.renderer.orchestrator import run_presentation
        from almanac.slides import SLIDES

        try:
            size = os.get_terminal_size()
            term_size = (size.columns, size.lines)
        except OSError:
            term_size = (80, 24)
        run_presentation(SLIDES, bundle, term_size)
    except KeyboardInterrupt:
        pass
