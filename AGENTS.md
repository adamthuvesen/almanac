# AGENTS.md — Almanac

Almanac — "Spotify Wrapped for your codebase." A Python 3.11+ CLI that reads `git log` from a local repo and emits a stats bundle (JSON), a one-line summary, an animated TTY presentation, or a self-contained HTML report.

User-level guidance (tone, principles, git etiquette) lives in `~/.claude/CLAUDE.md` and `~/dotfiles/agents/AGENTS.md` and is *not* duplicated here. This file is for project-specific facts. `CLAUDE.md` is a symlink to this file — edit `AGENTS.md`.

## Layout

```
almanac/
├── window.py        Resolve --year/--since/--until into a Window
├── ingest.py        git log subprocess → Commit list
├── stats.py         Aggregate commits → schema_version:1 bundle
├── classifier/      Layered commit-subject classifier (rules + zeroshot)
├── renderer/        TTY orchestrator, HTML, PNG, one-line consumers
├── slides/          One Slide per TTY screen; registry in __init__.py
├── templates/       almanac.html/css/js + card.html for HTML/PNG output
└── cli.py           Entry point (almanac.cli:main)

tests/               pytest suite; test_smoke_self.py runs the CLI on this repo
docs/                Subsystem docs — see Index
```

## Quickstart

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"           # base + dev
uv pip install -e '.[ml]'            # optional: torch/transformers for zero-shot
uv pip install -e '.[png]'           # optional: playwright for --png

almanac                              # current repo, last 12 months, TTY if interactive
almanac --json                       # full stats bundle on stdout
almanac --html                       # render + open HTML report
almanac --classifier {auto,rules,zeroshot}

uv run pytest tests/ -q              # tests
uv run ruff check .                  # lint
uv run ruff format --check .         # format check
```

## Critical Conventions

- **The JSON bundle is the contract.** Renderers consume `schema_version: 1` and stay independent of the ingest/stats engine. Add a slide → keep TTY and HTML in sync against the bundle, not a Python type.
- **Author-local time everywhere.** `window.py` resolves dates from commit `%aI` wall-clock; bare `YYYY-MM-DD` in `--until` is inclusive of the end day. All buckets (`by_hour`, `by_dow`) follow this — don't switch to UTC without updating every bucket.
- **`git log --numstat -z` is required.** NUL-terminated output is the only mode where tabs/newlines in filenames parse correctly; see [almanac/ingest.py](almanac/ingest.py) and `tests/test_ingest_parser.py`.
- **HTML output path is a random-suffixed tempfile.** Don't "simplify" [almanac/renderer/html.py](almanac/renderer/html.py) to a predictable name — that's a symlink hijack.
- **Never commit secrets, `.env`, or AI-attribution lines.**

## Read The Docs First

Before editing a subsystem, read the matching `docs/*.md`:

- **Architecture / pipeline** → [architecture.md](docs/architecture.md)
- **Commit classifier** (rules + zeroshot, preprocess, cache) → [classifier.md](docs/classifier.md)
- **TTY + HTML renderers** (slides, themes, escaping) → [rendering.md](docs/rendering.md)

If a doc disagrees with code, fix the doc in the same change.

## Safety invariants (don't regress these)

- HTML report makes **zero outbound requests by default**. Gravatar avatars only via `--gravatar` (emits `md5(email)` for top authors).
- Never crash on hostile commit data: non-UTF-8 bytes decode with `errors="replace"`; commit subjects / author names / paths are HTML-escaped at render time; ESC and C0 control bytes are stripped in the TTY renderer so a hostile commit can't clear the screen.

## Reserved/stub flags

`--demo` is supported (synthetic bundle, no git). `--png` requires the optional `almanac[png]` extra and a one-time `playwright install chromium` for share-card export.

These are still registered but not implemented: `--voice`, `--soundtrack`, `--slides` (they print `not yet implemented` and exit 1). Do not re-purpose them quietly.

## Index

Start in [architecture.md](docs/architecture.md), then follow the subsystem docs above.
