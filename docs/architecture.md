# Architecture

The pipeline is a straight line, and each stage is independently testable:

```
cli.py → window.resolve_window → ingest.iter_commits → stats.compute_bundle → renderer/{orchestrator,html,one-line}
```

The JSON bundle (`schema_version: 1`) is the contract between the engine
(ingest + stats) and the renderers. Renderers consume the bundle and are
independent of any Python type — add a slide and both TTY and HTML should stay
in sync against the bundle, not a shared dataclass.

## `almanac/window.py`

Resolves `--year` / `--since` / `--until` into a `Window` in the
**author-local** convention (wall-clock from commit `%aI`). Bare `YYYY-MM-DD` in
`--until` is **inclusive of the end day**; default is trailing 12 months. All
downstream buckets (`by_hour`, `by_dow`) use this same convention. Don't switch
to UTC without updating every bucket.

## `almanac/ingest.py`

Single `git log --numstat -z --pretty=format:...` subprocess. Parses
NUL-terminated records (renames emit an empty path + two extra NUL tokens;
binary files show `-\t-`). Non-UTF-8 bytes are decoded with `errors="replace"` —
never crash on hostile commit data. `coalesce_identities` merges author emails
by name similarity; `Commit.is_merge` is derived from `len(parents) > 1`.

`git log --numstat -z` (NUL-terminated) is required — tabs/newlines in filenames
parse correctly only in `-z` mode. See `tests/test_ingest_parser.py`.

## `almanac/stats.py`

Pure-Python aggregation over the in-memory commit list. Produces the
`schema_version: 1` bundle (commit_count, verbs, by_dow, by_hour,
lines_added/removed, biggest_commit, streak/gap, files_by_churn, languages,
authors, subjects_sample). Every verb key in `BUNDLE_VERB_KEYS` is always
present, even when zero.

## Commit classifier

The layered commit-subject classifier lives in `almanac/classifier/`. See
[classifier.md](classifier.md).

## Renderers

Two consumers of the same bundle — TTY (`orchestrator.py`) and HTML
(`html.py`). See [rendering.md](rendering.md).
