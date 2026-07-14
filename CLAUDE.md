# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**cuttlefish** is an "agentic" static site generator, published as `cuttlefish-ssg` with the CLI entry point `ctf`. A generated site is described entirely by files — `config.toml`, Markdown content, Jinja2 templates, and a single stylesheet — which a coding agent edits in response to plain-language requests. There are no themes, no CSS framework, and nothing to compile or bundle. The generated site ships an `AGENTS.md` that is the agent's contract for editing *that* site; this repo builds the tool that renders it.

This distinction matters: this repo is the **generator** (the `cuttlefish` Python package). The starter site it emits lives under `src/cuttlefish/scaffold/site/` and is a *template payload*, not part of the generator's own runtime.

**No plugin API — extend by editing, grow the core deliberately.** Because a coding agent edits a site's files directly, cuttlefish has no plugin/hook system and should not grow one. Reusable *presentation* features (breadcrumbs, reading time, comments) are packaged as **recipes** — markdown guides that an agent applies by editing a site's templates, CSS, and optional client-side JS, plus any custom values under the free-form `[params]` table. A recipe is **additive**: `[params]` is its only config surface. It never edits the structural tables (`content_types`, `taxonomies`, `nav`) that define the site — those are contract-authored, and a recipe that depends on one *states it as a prerequisite* rather than editing it, so the recipe stays an independent add-on. Recipes live in the repo's top-level **`recipes/`** as an example library (see `recipes/README.md` for the format and authoring rules); they are deliberately **not** shipped in the wheel or copied into generated sites — a user browses the gallery and copies/pastes the one they want into their site. Each is a markdown file with `+++` TOML front matter of just `name` + `description` (the one-line `description` is the index for browsing the library) followed by the steps to apply. The handful of features that genuinely need to run *during* the build — RSS/Atom, a search index — should be **absorbed into core rather than exposed through a plugin API**: there aren't enough of them to justify the machinery, and each one built in-core stays inside the incremental-build correctness model (fingerprints, pruning, the single build path) instead of punching a hole in it.

## Commands

```bash
uv run python -m pytest              # run the full test suite
uv run python -m pytest -q           # quiet
uv run python -m pytest tests/test_content.py::test_split_front_matter_basic  # single test
uv run ctf init <dir>                # scaffold a new site
uv run ctf build <root>              # render a site to public/
uv run ctf check <root>              # validate config/content/templates, write nothing
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

**The summary/body split.** Listing pages (type indexes, taxonomy pages, taxonomy indexes, home) receive a restricted `ContentSummary` view (`content.py`) that deliberately **omits `body_html`**. Single-content and standalone-page templates get the full `ContentItem`. This is not just encapsulation — it is what makes incremental builds correct: because no listing can render a body, a body-only edit provably cannot change any listing, so listings are safely skipped. Do not add body content to `ContentSummary` or pass full `ContentItem`s to aggregate templates; it silently breaks incremental correctness.

**Aggregates are fingerprinted, never body-hashed.** An *aggregate* is any page listing multiple items (type index, taxonomy term page, taxonomy index, home). Each is described by an `AggregateSpec` (`graph.py`) carrying a `fingerprint` computed over exactly the summary data it renders — via `ContentItem.meta_fingerprint`, which hashes title/date/description/slug/url/taxonomies/draft and **never** the body. An aggregate rebuilds only if its fingerprint changed or its template was (transitively) affected.

### Incremental builds

`.ctf/cache.json` (a `Manifest`) records the previous build: a `config_hash`, per-content file hashes, per-template hashes + refs, static hashes, and aggregate fingerprints. There is a **single build routine** (`build.py::_run_build`) that renders whatever differs from a given manifest:

- A build is incremental only when a manifest exists, `public/` exists, and `config_hash` matches — then `_run_build` runs against that manifest. Otherwise it runs the **full** variant: `public/` is cleared and `_run_build` runs against an *empty* `Manifest()`, so every page/aggregate/static file registers as changed and is rebuilt. Full is not a separate implementation — it is the same routine with a blank slate, so the two modes cannot drift out of agreement.
- `config_hash` includes the effective `base_path`, so switching between `ctf build` and `ctf serve` (which forces `base_path=""`) correctly invalidates the cache.
- **Template dependencies** (`template_deps.py::TemplateGraph`) track `{% extends %}`/`{% include %}` edges. A changed base/partial invalidates every template that transitively uses it via `affected_by`.
- **Pruning**: outputs present in the old manifest but not the new one (deleted content, renamed slugs, removed terms) are deleted, and now-empty directories cleaned up. (A full build clears `public/` up front, and prunes against the empty manifest — a no-op — so the same code covers both.)

When touching build logic, preserve the single-path property: full and incremental must stay one routine. `tests/test_incremental.py::test_incremental_output_matches_full` guards this by asserting a sequence of incremental rebuilds is byte-identical to a forced full build.

### Error handling

User-fixable problems raise `CuttlefishError` subclasses (`ConfigError`, `ContentError`, `RenderError`, `PermalinkError`) carrying a two-tier `summary` (the failed operation) + `detail` (the specific reason). The CLI's `handle_errors` decorator (`cli.py`) prints these as a flat, styled `error:` diagnostic and exits non-zero; anything else propagates as a real traceback (it's a bug). `cli.py::main` also routes Click/Typer usage errors through the same flat renderer so all diagnostics share one visual language. When adding a failure mode the user can act on, raise a `CuttlefishError` subclass with an actionable message — do not print and exit ad hoc.

## Conventions

- Python 3.11+, `from __future__ import annotations` everywhere, typed dataclasses (config types are `frozen=True`).
- Config/content dataclasses are the boundary of truth: validate at parse time in `config.py` rather than defensively downstream.
- Comments in this codebase explain **why** (especially the non-obvious invariants above), not what. Match that when editing.
- Conventional Commits (see the global instruction). Note `!` for breaking changes, e.g. `feat(content)!: ...`.
- Tests mirror the source: unit tests live in `tests/test_<module>.py` (e.g. `test_config.py`, `test_content.py`) covering that one module. Cross-module behavior goes in the integration suites — `test_end_to_end.py` (a full `build_site` of the scaffold) and `test_incremental.py` (the incremental dependency graph). Put a new unit test with its module's file, not in a grab-bag.

## The scaffold payload

`src/cuttlefish/scaffold/site/` is copied verbatim by `ctf init`. Its `AGENTS.md`, `config.toml`, templates, and `static/css/main.css` are the reference for the site-authoring contract (config schema, permalink tokens, template variables like `recent.<type>`, `featured.<type>`, `taxonomies.<name>`, `site.profile`). When you change what the generator supports (a new config key, a new template variable), update this scaffold — especially `AGENTS.md` — so generated sites document it. `.gitignore` deliberately anchors `/site/` (mkdocs output) so it does not match this scaffolded `site/`.

The human-facing docs in `docs/` (rendered by mkdocs) are the **canonical prose reference** for the same site-authoring contract; the scaffold `AGENTS.md` is its compressed, agent-facing counterpart. A change to what the generator supports must land in **both** — update the relevant `docs/*.md` page alongside the scaffold, or the two drift apart.
