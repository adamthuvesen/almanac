# Renderers (TTY + HTML)

Two consumers of the same JSON bundle, both independent of the ingest/stats
engine. If you add a slide, both TTY and HTML should stay in sync — the bundle
is the shared contract, not any Python type.

## TTY presentation

`almanac/renderer/orchestrator.py` drives the TTY presentation: raw-mode stdin,
alt-screen, ANSI cursor control, one `Slide` per screen. Slides live in
`almanac/slides/` (cover, numbers, cadence, top_files, languages, verbs,
authors) and implement a `Slide` protocol with a `render(bundle, term_size) →
str` method. The registry lives in `slides/__init__.py:SLIDES`.

ESC and C0 control bytes are stripped in the TTY renderer so a hostile commit
can't clear the screen.

## HTML report

`almanac/renderer/html.py` renders
[almanac/templates/almanac.html](../almanac/templates/almanac.html) via
`string.Template.safe_substitute`, injecting the bundle as `BUNDLE_JSON` with
`</`, U+2028, U+2029 escaped so string content can't break out of the `<script>`
tag.

Default output path is a random-suffixed `tempfile.NamedTemporaryFile` — don't
"simplify" this to a predictable name (symlink hijack).

The HTML report makes **zero outbound requests by default**. Gravatar avatars
appear only via `--gravatar` (emits `md5(email)` for top authors). Commit
subjects, author names, and paths are HTML-escaped at render time.

`--theme` applies to HTML output: `classic`, `terminal`, `midnight`, `paper`,
`wrapped`.
