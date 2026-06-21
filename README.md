# ass — agentic static site generator

A static site generator designed to be driven by an **agent**. You describe your
site in plain, well-structured files — `config.toml`, Jinja2 templates, and
Markdown content — and an agent can safely add content types, taxonomies,
templates, and theming by editing those files.

## Features

- **Content types** (blog, project, …) each with their own template, permalink,
  and index page.
- **Taxonomies** (tags, categories, …) declared in config, applied via front
  matter, with per-term pages and a taxonomy index.
- **Standalone pages** (about, etc.) that belong to no type index or taxonomy.
- **Configurable home/landing page.**
- **Incremental builds** that only re-render what changed.
- **`serve`** with file watching and browser live-reload.

## Quick start

```bash
uv sync
uv run ass init mysite
cd mysite
uv run ass serve      # live preview at http://127.0.0.1:8000 (watch + reload)
uv run ass build      # produce public/
```

Every scaffolded site ships an `AGENTS.md` (and `CLAUDE.md`) that documents how
to edit config, author content, and customize templates/theming.

## Commands

| Command | What it does |
|---------|--------------|
| `ass init <dir>` | Scaffold a new site (refuses a non-empty dir unless `--force`). |
| `ass build [--force] [--drafts]` | Build into `public/`. `--force` ignores the cache; `--drafts` includes `draft = true`. |
| `ass serve [--port] [--no-reload]` | Build, serve `public/`, watch inputs, and live-reload the browser. |

## Site layout

```
mysite/
  AGENTS.md / CLAUDE.md   # agent instructions
  config.toml             # site config (types, taxonomies, home)
  content/<type>/*.md     # content with +++ TOML front matter
  content/pages/*.md      # standalone pages
  templates/*.html        # Jinja2 templates
  static/**               # copied to the site root
  public/                 # generated output
  .ass/cache.json         # build manifest (incremental builds)
```

## Incremental builds

`ass` keeps a manifest (`.ass/cache.json`) and only re-renders what changed:

- A **body-only** content edit rebuilds just that page — listings are skipped.
- A **front-matter** edit (title/date/summary/tags) also rebuilds the listings
  that show it (type index, taxonomy term pages, home).
- A **template** edit rebuilds exactly the pages that use it (transitively, via
  `extends`/`include`); editing `base.html` rebuilds everything.
- A **config** change forces a full rebuild.
- Deleted content and renamed slugs prune their stale output files.

This is correct because listing templates only ever see summary fields, never a
post's rendered body (enforced in the renderer and documented in `AGENTS.md`).

## Development

```bash
uv run pytest
```
