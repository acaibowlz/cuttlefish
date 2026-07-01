# Agent guide for this `cuttlefish` site

This site is built by **cuttlefish** (agentic static site generator). You (the agent)
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
| `.ctf/` | **Generated** build cache. Never edit by hand. | ❌ |

Build with `ctf build`. Preview live with `ctf serve` (watches files and
reloads the browser). A `public/sitemap.xml` of every page is generated
automatically when `base_url` is set.

## Editing `config.toml`

Top-level keys: `title`, `base_url`, and the tables below. `base_url` is the
site's absolute origin (e.g. `https://example.com`); it builds absolute URLs
such as the `sitemap.xml` entries, so set it for production. If it includes a
**subpath** (e.g. `https://you.github.io/repo`), that path (`/repo`) is
prefixed to every internal link and asset automatically, so the site works when
served under a subfolder — a GitHub Pages project site, for example. `ctf serve`
ignores the subpath and previews at the local root.

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
multiple = false                      # single term (default true = list)
```

Apply it by adding the key to a content file's front matter. `multiple`
decides the front-matter shape: `true` (default) requires a list
(`tags = ["python", "ssg"]`); `false` requires a single string
(`category = "AI"`). The wrong shape is a build error.

### The `pages` type

`[content_types.pages]` is special: standalone pages with **no** index and no
taxonomy participation. Do **not** give it `index_template`/`index_permalink`.

### Home page

```toml
[home]
template = "home.html"
recent = { blog = 5, project = 3 }   # sections: content-type = how many recent items
```

`recent` is a table of `content-type = count`. Each becomes a section the home
template reads by key as `recent.<type>` (e.g. `recent.blog`) — a list of
summary-only items — so you can show several types and order/title them freely.
Every key must name a declared content type.

### Navigation bar

```toml
[nav]
enabled = true                          # set false to hide the nav
labels = ["Blog", "Projects", "About"]  # display text
links  = ["/blog/", "/projects/", "/about/"]  # hrefs (paired with labels by position)
```

`labels` and `links` must have the **same number of entries** (they are paired
by position). Templates access them via `site.nav.enabled` and `site.nav.items`
(each item has `.label` and `.link`).

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
- `draft = true` hides a page from `ctf build` (shown by `ctf serve`).

## Permalink tokens

Usable in any `permalink`/`index_permalink`: `{slug}`, `{type}`, `{year}`,
`{month}`, `{day}` (from `date`), `{term}`, `{taxonomy}`.

## Theming & templates

Templates are Jinja2 and live in `templates/`. `base.html` is the shared layout;
others `{% extends "base.html" %}`. A global `site` object is available
everywhere: `site.title`, `site.base_url`, `site.nav`, and `site.config` (the
raw parsed `config.toml`).

Variables per template kind:

| Template | Variables |
|----------|-----------|
| single content (`blog.html`) | `page` / `item` (full, incl. `page.body_html`), `type`, `terms` |
| type index (`blog.index.html`) | `items` (summary only), `page` (pagination), `type` |
| taxonomy term (`taxonomy.html`) | `taxonomy`, `term`, `items` (summary only) |
| taxonomy index (`taxonomy.index.html`) | `taxonomy`, `terms` |
| home (`home.html`) | `recent` — map of content-type → summary-only items (`recent.blog`) |

> **Important rule:** listing templates (index / taxonomy / taxonomy-index /
> home) may use only **summary fields** — `title`, `date`, `summary`, `slug`,
> `url`, `taxonomies`, `draft`. The full rendered body (`body_html`) is
> available **only** in single-content and page templates. This keeps
> incremental builds correct: editing a post's body never forces listings to
> rebuild.

Single-content templates also receive `terms`: a mapping of taxonomy name to a
list of `{name, url}` objects, so content can link each term to its term page —
e.g. `{% for term in terms.get('tags') or [] %}<a href="{{ term.url }}">{{
term.name }}</a>{% endfor %}`.

Reference static assets by absolute path (e.g. `/css/main.css`); `static/` is
copied to the site root, so `static/css/main.css` → `/css/main.css`.

### Styling

Styling is **plain CSS** in `static/css/main.css`, linked once from `base.html`.
There is no asset pipeline and no CSS framework: `static/` is copied verbatim,
so whatever you write ships as-is. Follow these conventions so the site stays
consistent as you edit it:

- **Use the design tokens, don't hardcode.** Colors, fonts, and layout are CSS
  custom properties on `:root`: surfaces (`--bg`, `--surface`, `--border`), text
  (`--fg`, `--muted`), accent (`--accent`, `--accent-hover`), typography
  (`--font-sans`, `--font-mono`), and shape/size (`--max-width`, `--radius`).
  Reference them with `var(--accent)` rather than repeating raw values. Need a
  new color or spacing value site-wide? Add a token to `:root` and use it
  everywhere, instead of sprinkling literals.
- **Respect dark mode.** The palette is themed via a `@media
  (prefers-color-scheme: dark)` block that overrides the same tokens. Because
  everything reads from tokens, you get light/dark for free — keep it that way by
  styling through tokens, not fixed colors.
- **Prefer semantic classes over utility soup or inline styles.** Style by
  meaning (`.post-list`, `.site-header`, `.tags`), not by appearance
  (`.mt-4`, `style="..."`). It keeps templates readable and changes localized to
  one stylesheet.
- **Keep markup and CSS in sync.** When you add a class in a template, add its
  rule to `main.css` in the same edit; when you remove markup, drop the dead
  rule. The two files are a pair.
- **Don't reach for a CSS framework by default.** You write clean CSS as easily
  as utility classes, and a framework (Tailwind, etc.) would mean a build step
  this project deliberately doesn't have. If the user explicitly wants one, treat
  it as an opt-in they've chosen — not the default.
