# AGENTS.md

Canonical instructions for AI coding agents working in this repository (Claude, Codex, Cursor, etc.). `CLAUDE.md` is a symlink to this file — edit `AGENTS.md`.

## Project

Almanac — "Spotify Wrapped for your codebase." A Python 3.11+ CLI that reads `git log` from a local repo and emits a stats bundle (JSON), a one-line summary, an animated TTY presentation, or a self-contained HTML report.

## Commands

```bash
# Setup (uv)
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"          # base + dev
uv pip install -e '.[ml]'           # optional: torch/transformers for zero-shot
uv pip install -e '.[png]'          # optional: playwright for --png (then: playwright install chromium)

# Run the CLI (entry point: almanac.cli:main)
almanac                              # current repo, last 12 months, TTY if interactive
almanac --json                       # full stats bundle on stdout
almanac --html                       # render + open HTML report
almanac --html-out report.html       # render HTML to path, no browser
almanac --png                        # 1200×630 share card → ./summary-card.png (needs almanac[png])
almanac --classifier {auto,rules,zeroshot}

# Tests (pytest configured via pyproject)
pytest -v --tb=short
pytest tests/test_classifier_rules.py::test_name   # single test
pytest -k "classifier and not zeroshot"            # filter

# Lint / format
ruff check . --fix && ruff format .
```

The `[ml]` extra is heavy (torch). Zero-shot tests are gated — most of the suite runs without it. `tests/test_smoke_self.py` runs the CLI against this repo itself as an end-to-end check.

## Architecture

The pipeline is a straight line, and each stage is independently testable:

```
cli.py → window.resolve_window → ingest.iter_commits → stats.compute_bundle → renderer/{orchestrator,html,one-line}
```

**`almanac/window.py`** — Resolves `--year` / `--since` / `--until` into a `Window` in the **author-local** convention (wall-clock from commit `%aI`). Bare `YYYY-MM-DD` in `--until` is **inclusive of the end day**; default is trailing 12 months. All downstream buckets (by_hour, by_dow) use this same convention. Don't switch to UTC without updating every bucket.

**`almanac/ingest.py`** — Single `git log --numstat -z --pretty=format:...` subprocess. Parses NUL-terminated records (renames emit an empty path + two extra NUL tokens; binary files show `-\t-`). Non-UTF-8 bytes are decoded with `errors="replace"` — never crash on hostile commit data. `coalesce_identities` merges author emails by name similarity; `Commit.is_merge` is derived from `len(parents) > 1`.

**`almanac/stats.py`** — Pure-Python aggregation over the in-memory commit list. Produces the `schema_version: 1` bundle (commit_count, verbs, by_dow, by_hour, lines_added/removed, biggest_commit, streak/gap, files_by_churn, languages, authors, subjects_sample). Every verb key in `BUNDLE_VERB_KEYS` is always present, even when zero.

**`almanac/classifier/`** — Layered commit-subject classifier, gated by `--classifier`:
1. `preprocess.py` strips PR suffixes `(#1234)`, bracketed tickets `[ABC-123]`, bare tickets `PROJ 821`, branch prefixes `alice/...`. Conventional Commits subjects are never altered.
2. `rules.py` matches CC regex (`feat(scope): ...`), then first-verb rules (`add→feat`, `bump→chore`, ~50 entries), then Renovate/Dependabot dependency-bump patterns.
3. `zeroshot.py` runs a local DeBERTa MNLI pipeline via `transformers`. Collapses to `unclear` below 0.35 confidence or when top-two margin < 0.05.
4. `cache.py` memoizes by `(preprocessed_subject, body)` so re-runs are cheap.

`auto` picks zeroshot if `transformers` imports, else `rules`. `zeroshot` errors out at CLI entry if the extra is missing, before any git work.

**`almanac/renderer/`** — Two consumers of the same bundle:
- `orchestrator.py` drives the TTY presentation: raw-mode stdin, alt-screen, ANSI cursor control, one `Slide` per screen. Slides live in `almanac/slides/` (cover, numbers, cadence, top_files, languages, verbs, authors) and implement a `Slide` protocol with a `render(bundle, term_size) → str` method. Registry lives in `slides/__init__.py:SLIDES`.
- `html.py` renders `templates/almanac.html` via `string.Template.safe_substitute`, injecting the bundle as `BUNDLE_JSON` with `</`, U+2028, U+2029 escaped so string content can't break out of the `<script>` tag. Default output path is a random-suffixed `tempfile.NamedTemporaryFile` — don't "simplify" this to a predictable name (symlink hijack).

**Renderers consume the JSON bundle and are independent of the ingest/stats engine.** If you add a slide, both TTY and HTML should stay in sync — the bundle is the shared contract, not any Python type.

## Safety invariants (don't regress these)

- HTML report makes **zero outbound requests by default**. Gravatar avatars only via `--gravatar` (emits `md5(email)` for top authors).
- Commit subjects / author names / paths are HTML-escaped at render time. ESC and C0 control bytes are stripped in the TTY renderer so a hostile commit can't clear the screen.
- `git log --numstat -z` (NUL-terminated) is required — tabs/newlines in filenames parse correctly only in `-z` mode. See `tests/test_ingest_parser.py`.

## OpenSpec

This repo uses OpenSpec (`openspec/`) for structured change tracking. Prefer the `/opsx:*` skills for non-trivial work: `/opsx:propose` → `/opsx:apply` → `/opsx:verify` → `/opsx:archive`. Archived proposals under `openspec/changes/archive/` are the best reference for how proposals are scoped in this project (short, with Non-goals + Success criteria sections, per `openspec/config.yaml`).

## Reserved/stub flags

`--demo` is supported (synthetic bundle, no git). `--png` requires the optional `almanac[png]` extra and a one-time `playwright install chromium` for share-card export.

These are still registered but not implemented: `--voice`, `--soundtrack`, `--slides` (they print `not yet implemented` and exit 1). Do not re-purpose them quietly.

`--theme` applies to HTML output (`classic`, `terminal`, `midnight`, `paper`, `wrapped`).
