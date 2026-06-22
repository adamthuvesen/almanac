# Commit classifier

`almanac/classifier/` is a layered commit-subject classifier, gated by
`--classifier {auto,rules,zeroshot}`:

1. `preprocess.py` strips PR suffixes `(#1234)`, bracketed tickets `[ABC-123]`,
   bare tickets `PROJ 821`, branch prefixes `alice/...`. Conventional Commits
   subjects are never altered.
2. `rules.py` matches CC regex (`feat(scope): ...`), then first-verb rules
   (`add→feat`, `bump→chore`, ~50 entries), then Renovate/Dependabot
   dependency-bump patterns.
3. `zeroshot.py` runs a local DeBERTa MNLI pipeline via `transformers`.
   Collapses to `unclear` below 0.35 confidence or when the top-two margin
   < 0.05.
4. `cache.py` memoizes by `(preprocessed_subject, body)` so re-runs are cheap.

`auto` picks zeroshot if `transformers` imports, else `rules`. `zeroshot` errors
out at CLI entry if the `[ml]` extra is missing, before any git work.

The `[ml]` extra is heavy (torch). Zero-shot tests are gated — most of the suite
runs without it.
