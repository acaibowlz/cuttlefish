# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**cuttlefish** is an "agentic" static site generator, published as `cuttlefish-ssg` with the CLI entry point `ctf`. A generated site is described entirely by files — `config.toml`, Markdown content, Jinja2 templates, and a single stylesheet — which a coding agent edits in response to plain-language requests. There are no themes, no CSS framework, and no asset pipeline. The generated site ships an `AGENTS.md` that is the agent's contract for editing *that* site; this repo builds the tool that renders it.

This distinction matters: this repo is the **generator** (the `cuttlefish` Python package). The starter site it emits lives under `src/cuttlefish/scaffold/site/` and is a *template payload*, not part of the generator's own runtime.

## Commands

```bash
uv run python -m pytest              # run the full test suite (58 tests)
uv run python -m pytest -q           # quiet
uv run python -m pytest tests/test_units.py::test_split_front_matter_basic  # single test
uv run ctf init <dir>                # scaffold a new site
uv run ctf build <root>              # render a site to public/
uv run ctf serve <root>             # live-reloading dev server (drafts on by default)
uv run mkdocs serve                  # preview the project docs (docs/)
```

Use `uv run python -m pytest`, **not** `uv run pytest`. The test modules do `from tests.conftest import ...`, which needs the repo root on `sys.path`; `python -m` provides that, bare `pytest` does not.

## Architecture

A build is a pipeline in `build.py::build_site`, which wires together small single-purpose modules:

1. **`config.py`** — loads and strictly validates `config.toml` into frozen dataclasses (`SiteConfig`, `ContentType`, `Taxonomy`, `HomeConfig`, `Profile`, `NavConfig`). Unknown keys are **rejected** (with a did-you-mean suggestion), because a silently-ignored typo is the worst failure mode for an agent-edited config. The sole exception is the free-form `[params]` table (`_parse_params`), exposed to templates as `site.params`: its contents are intentionally *not* key-checked, so it's the one place custom site-wide values can live without tripping the validator.
2. **`content.py`** — discovers `content/<type>/*.md`, splits `+++`-fenced TOML front matter from the Markdown body, and renders the body to HTML with `mistune`. Produces `ContentItem`.
3. **`taxonomy.py`** — groups items by each configured taxonomy's terms into `TaxonomyData`/`Term`.
4. **`permalink.py`** — substitutes tokens (`{slug}`, `{year}`, `{term}`, …) in permalink patterns and maps URLs to "pretty URL" output paths (`/blog/post/` → `public/blog/post/index.html`).
5. **`render.py`** — `Renderer` wraps a Jinja2 `Environment` (StrictUndefined, autoescape) and writes pages. It also handles pagination and subpath link rewriting.
6. **`sitemap.py`** — emits `sitemap.xml` from the build's page outputs (needs `base_url`).
7. **`cache.py` / `graph.py` / `template_deps.py`** — the incremental-build machinery (see below).

### Two invariants that shape the whole design

**The summary/body split.** Listing pages (type indexes, taxonomy pages, taxonomy indexes, home) receive a restricted `ListingItem` view (`content.py`) that deliberately **omits `body_html`**. Single-content and standalone-page templates get the full `ContentItem`. This is not just encapsulation — it is what makes incremental builds correct: because no listing can render a body, a body-only edit provably cannot change any listing, so listings are safely skipped. Do not add body content to `ListingItem` or pass full `ContentItem`s to aggregate templates; it silently breaks incremental correctness.

**Aggregates are fingerprinted, never body-hashed.** An *aggregate* is any page listing multiple items (type index, taxonomy term page, taxonomy index, home). Each is described by an `AggregateSpec` (`graph.py`) carrying a `fingerprint` computed over exactly the listing-relevant data it renders — via `ContentItem.meta_fingerprint`, which hashes title/date/description/slug/url/taxonomies/draft and **never** the body. An aggregate rebuilds only if its fingerprint changed or its template was (transitively) affected.

### Incremental builds

`.ctf/cache.json` (a `Manifest`) records the previous build: a `config_hash`, per-content file hashes, per-template hashes + refs, static hashes, and aggregate fingerprints. On the next build (`_incremental_build`):

- A build is incremental only when a manifest exists, `public/` exists, and `config_hash` matches. Otherwise it falls back to `_full_build` (which clears `public/`).
- `config_hash` includes the effective `base_path`, so switching between `ctf build` and `ctf serve` (which forces `base_path=""`) correctly invalidates the cache.
- **Template dependencies** (`template_deps.py::TemplateGraph`) track `{% extends %}`/`{% include %}` edges. A changed base/partial invalidates every template that transitively uses it via `affected_by`.
- **Pruning**: outputs present in the old manifest but not the new one (deleted content, renamed slugs, removed terms) are deleted, and now-empty directories cleaned up.

When touching build logic, keep `_full_build` and `_incremental_build` in agreement — they must produce identical `public/` output and write equivalent manifests; the incremental path is purely an optimization of the full one.

### Error handling

User-fixable problems raise `CuttlefishError` subclasses (`ConfigError`, `ContentError`, `RenderError`, `PermalinkError`) carrying a two-tier `summary` (the failed operation) + `detail` (the specific reason). The CLI's `handle_errors` decorator (`cli.py`) prints these as a flat, styled `error:` diagnostic and exits non-zero; anything else propagates as a real traceback (it's a bug). `cli.py::main` also routes Click/Typer usage errors through the same flat renderer so all diagnostics share one visual language. When adding a failure mode the user can act on, raise a `CuttlefishError` subclass with an actionable message — do not print and exit ad hoc.

## Conventions

- Python 3.11+, `from __future__ import annotations` everywhere, typed dataclasses (config types are `frozen=True`).
- Config/content dataclasses are the boundary of truth: validate at parse time in `config.py` rather than defensively downstream.
- Comments in this codebase explain **why** (especially the non-obvious invariants above), not what. Match that when editing.
- Conventional Commits (see the global instruction). Note `!` for breaking changes, e.g. `feat(content)!: ...`.

## The scaffold payload

`src/cuttlefish/scaffold/site/` is copied verbatim by `ctf init`. Its `AGENTS.md`, `config.toml`, templates, and `static/css/main.css` are the reference for the site-authoring contract (config schema, permalink tokens, template variables like `recent.<type>`, `featured.<type>`, `taxonomies.<name>`, `site.profile`). When you change what the generator supports (a new config key, a new template variable), update this scaffold — especially `AGENTS.md` — so generated sites document it. `.gitignore` deliberately anchors `/site/` (mkdocs output) so it does not match this scaffolded `site/`.
