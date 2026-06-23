# Agent guide for this `ass` site

This site is built by **ass** (agentic static site generator). You (the agent)
drive it by editing plain files. This document is the source of truth for how.

## Project map

| Path | What it is | Edit? |
|------|-----------|-------|
| `config.toml` | Whole-site configuration (types, taxonomies, home). | ✅ |
| `content/<type>/*.md` | Content for a content type (e.g. `blog`, `project`). | ✅ |
| `content/pages/*.md` | Standalone pages (no index, no taxonomy). | ✅ |
| `templates/*.html` | Jinja2 templates (theming & layout). | ✅ |
| `static/**` | CSS/JS/images copied verbatim to the site root. | ✅ |
| `public/` | **Generated** output. Never edit by hand. | ❌ |
| `.ass/` | **Generated** build cache. Never edit by hand. | ❌ |

Build with `ass build`. Preview live with `ass serve` (watches files and
reloads the browser).

## Editing `config.toml`

Top-level keys: `title`, `base_url`, and the tables below.

### Add a content type

```toml
[content_types.note]
template = "note.html"            # single-item template (required)
index_template = "note.index.html"  # listing template (omit for no index)
permalink = "/notes/{slug}/"      # required
index_permalink = "/notes/"       # required if index_template is set
paginate = 10                     # optional; 0/absent = no pagination
sort_by = "date"                  # front-matter field to sort by
order = "desc"                    # "desc" = newest/largest first, "asc" = oldest/smallest
```

Then create `templates/note.html` and `templates/note.index.html`, and put
content in `content/note/*.md`.

### Add a taxonomy

```toml
[taxonomies.category]
template = "taxonomy.html"            # term page (required)
index_template = "taxonomy.index.html"  # all-terms page (optional)
permalink = "/categories/{term}/"     # required
index_permalink = "/categories/"      # required if index_template is set
```

Apply it by adding the key to a content file's front matter:
`category = ["tutorials"]`.

### The `pages` type

`[content_types.pages]` is special: standalone pages with **no** index and no
taxonomy participation. Do **not** give it `index_template`/`index_permalink`.

### Home page

```toml
[home]
template = "home.html"
recent = { type = "blog", count = 5 }   # optional aggregation for the landing page
```

## Authoring content

Each file starts with a TOML front-matter block fenced by `+++`, then Markdown:

```
+++
title = "My Post"
date = 2026-06-21
summary = "One-line summary used in listings."
draft = false
tags = ["python", "ssg"]   # any configured taxonomy name
slug = "my-post"           # optional; defaults to the filename
+++

# Markdown body here
```

- A file's **content type** is its folder under `content/` (e.g.
  `content/blog/x.md` → type `blog`).
- `draft = true` hides a page from `ass build` (shown by `ass serve`).

## Permalink tokens

Usable in any `permalink`/`index_permalink`: `{slug}`, `{type}`, `{year}`,
`{month}`, `{day}` (from `date`), `{term}`, `{taxonomy}`.

## Theming & templates

Templates are Jinja2 and live in `templates/`. `base.html` is the shared layout;
others `{% extends "base.html" %}`. A global `site` object is available
everywhere: `site.title`, `site.base_url`, and `site.config` (the raw parsed
`config.toml`).

Variables per template kind:

| Template | Variables |
|----------|-----------|
| single content (`blog.html`) | `page` / `item` (full, incl. `page.body_html`), `type` |
| type index (`blog.index.html`) | `items` (summary only), `page` (pagination), `type` |
| taxonomy term (`taxonomy.html`) | `taxonomy`, `term`, `items` (summary only) |
| taxonomy index (`taxonomy.index.html`) | `taxonomy`, `terms` |
| home (`home.html`) | `recent` (summary only) |

> **Important rule:** listing templates (index / taxonomy / taxonomy-index /
> home) may use only **summary fields** — `title`, `date`, `summary`, `slug`,
> `url`, `taxonomies`, `draft`. The full rendered body (`body_html`) is
> available **only** in single-content and page templates. This keeps
> incremental builds correct: editing a post's body never forces listings to
> rebuild.

Reference static assets by absolute path (e.g. `/css/main.css`); `static/` is
copied to the site root, so `static/css/main.css` → `/css/main.css`.
