# Agent guide for this `cuttlefish` site

This site is built by **cuttlefish** (agentic static site generator). You (the
agent) drive its **look, layout, and configuration** by editing plain files. You
do **not** write the site's content — the author owns that. This document is the
source of truth for how.

## Project map

| Path | What it is | Edit? |
|------|-----------|-------|
| `config.toml` | Whole-site configuration (types, taxonomies, home). | ✅ |
| `templates/*.html` | Jinja2 templates (theming & layout). | ✅ |
| `static/**` | CSS/JS/images copied verbatim to the site root. | ✅ |
| `content/<type>/*.md` | Content for a content type (e.g. `blog`, `project`). **Author-owned — read for context, never write.** | ❌ |
| `content/pages/*.md` | Standalone pages (no index, no taxonomy). **Author-owned.** | ❌ |
| `public/` | **Generated** output. Never edit by hand. | ❌ |
| `.ctf/` | **Generated** build cache. Never edit by hand. | ❌ |

**Do not create, edit, delete, or rewrite content files** (`content/**/*.md`) —
not their front matter and not their Markdown bodies. The author writes the
words; your job is the config, templates, and styling that present them. You may
**read** content (e.g. to see which taxonomy terms or front-matter fields exist
so you can wire up config and templates), but treat it as read-only input.

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

Then create `templates/note.html` and `templates/note.index.html`. The author
adds the content under `content/note/*.md`.

### Add a taxonomy

```toml
[taxonomies.category]
template = "taxonomy.html"            # term page (required)
index_template = "taxonomy.index.html"  # all-terms page (optional)
permalink = "/categories/{term}/"     # required
index_permalink = "/categories/"      # required if index_template is set
multiple = false                      # single term (default true = list)
sort_by = "name"                      # term ordering: "name" (default) or "count"
order   = "asc"                       # "asc" (default) or "desc"
home    = true                        # also surface its terms on the home page
```

It is applied by adding the key to a content file's front matter (the author
does this). `multiple` decides the front-matter shape: `true` (default) requires a list
(`tags = ["python", "ssg"]`); `false` requires a single string
(`category = "AI"`). The wrong shape is a build error.

`sort_by`/`order` set how this taxonomy's terms are ordered **wherever they are
listed** — the term index page *and* the home list (below) share one ordering.
`sort_by` is `"name"` (the term text, default) or `"count"` (most-used first);
`order` is `"asc"` (default) or `"desc"`. Equal counts fall back to name. Set
`home = true` (default `false`) to also surface the terms on the landing page.

### The `pages` type

`[content_types.pages]` is special: standalone pages with **no** index and no
taxonomy participation. Do **not** give it `index_template`/`index_permalink`.

### Home page

```toml
[home]
template = "home.html"
recent   = { blog = 5, project = 3 }  # sections: content-type = how many recent items
featured = { blog = 2 }               # curated: content-type = how many featured items
profile  = true                       # render the [profile] block (see below)
```

`recent` is a table of `content-type = count`. Each becomes a section the home
template reads by key as `recent.<type>` (e.g. `recent.blog`) — a list of
summary-only items — so you can show several types and order/title them freely.
Every key must name a declared content type.

`featured` has the **same shape** and is read as `featured.<type>`, but is drawn
only from items with `featured = true` in their front matter (newest first). It
is independent of `recent` — use either, both, or neither. Every key must name a
declared content type.

A taxonomy with `home = true` (set on `[taxonomies.<name>]`, see *Add a
taxonomy*) is surfaced on the home page, read by key as `taxonomies.<name>`
(e.g. `taxonomies.tags`) — a list of terms, each with `name`, `count` and `url`,
ordered by that taxonomy's `sort_by`/`order`. Use it for a tag cloud
(`sort_by = "count"`) or a category list (`sort_by = "name"`). All terms are
passed; slice in the template if you want fewer.

`[home] profile = true` renders the site author block on the home page (see
`[profile]` below). The home template then receives a `profile` variable; it is
`None` when the toggle is off, so gate the block on `{% if profile %}`.

### Author profile

```toml
[profile]
name   = "Your Name"
bio    = "A short bio."
avatar = "/img/avatar.svg"                     # path under static/
email  = "you@example.com"
socials = { github = "https://github.com/you", mastodon = "https://…" }
```

Site-wide author details, available on **every** page as `site.profile`
(`.name`, `.bio`, `.avatar`, `.email`, `.socials`). `socials` is a
`platform → url` table and keeps config order, so links render in the order you
write them and the key is the platform name (handy for icon classes). Avatar's
`alt` should default to the name. Turn the home-page block on with
`[home] profile = true`.

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

## Content format (reference)

Content is **author-owned** — you don't write or edit it (see the project map).
This section documents the format the author uses so you can read it correctly
when wiring up config and templates. Each file starts with a TOML front-matter
block fenced by `+++`, then Markdown:

```
+++
title = "My Post"
date = 2026-06-21
description = "One-line description used in listings."
draft = false
featured = true            # optional; include in the home [home].featured sections
tags = ["python", "ssg"]   # any configured taxonomy name
slug = "my-post"           # optional; defaults to the filename
+++

# Markdown body here
```

- A file's **content type** is its folder under `content/` (e.g.
  `content/blog/x.md` → type `blog`).
- **Required for every non-`pages` type:** `title`, `description`, and `date`.
  A missing one fails the build with the offending file named.
- `date` **must be a plain `YYYY-MM-DD` date** — an unquoted TOML date
  (`date = 2026-06-21`). A quoted string (`"2026-06-21"`) and a date-time with a
  time component (`2026-06-21T09:30:00Z`) are both rejected; the parser also
  validates the calendar date, so an impossible date fails too.
- The **`pages`** type is exempt — a standalone page needs none of these; its
  slug defaults to the filename.
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
| single content (`blog.html`) | `page` / `item` (full, incl. `page.body_html` and `page.toc`), `type`, `terms` |
| type index (`blog.index.html`) | `items` (summary only), `page` (pagination), `type` |
| taxonomy term (`taxonomy.html`) | `taxonomy`, `term`, `items` (summary only) |
| taxonomy index (`taxonomy.index.html`) | `taxonomy`, `terms` |
| home (`home.html`) | `recent` and `featured` — maps of content-type → summary-only items (`recent.blog`, `featured.blog`); `taxonomies` — map of taxonomy → terms with `name`/`count`/`url` (`taxonomies.tags`); `profile` — the `[profile]` block or `None` (also on every page as `site.profile`) |

> **Important rule:** listing templates (index / taxonomy / taxonomy-index /
> home) may use only **listing fields** — `title`, `date`, `description`,
> `slug`, `url`, `taxonomies`, `draft`. The full rendered body (`body_html`) is
> available **only** in single-content and page templates. This keeps
> incremental builds correct: editing a post's body never forces listings to
> rebuild.

Single-content templates also receive `terms`: a mapping of taxonomy name to a
list of `{name, url}` objects, so content can link each term to its term page —
e.g. `{% for term in terms.get('tags') or [] %}<a href="{{ term.url }}">{{
term.name }}</a>{% endfor %}`.

`page.toc` is a flat, in-order list of the body's headings, one entry per
heading, each with `level` (1–6), `text` (plain-text label), `id` (the slug set
as the heading's `id` in `body_html`), and `url` (the `#id` anchor). It is empty
when the body has no headings. Build a table of contents by looping over it and
indenting on `level` — e.g. `{% for h in page.toc %}<a href="{{ h.url }}">{{
h.text }}</a>{% endfor %}`. The matching `id` attributes are already present in
`page.body_html`, so the anchors resolve without extra work.

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
- **Keep it responsive.** Responsive, mobile-first layout is the goal on any
  screen — however you build, size layout in relative units (`rem`/`%`/`ch`) or
  `clamp()` rather than fixed pixel widths, let content reflow, and make images
  scale (`max-width: 100%`); `base.html` sets the `viewport` meta tag. The
  starter theme only *demonstrates* one way (you're free to restyle or replace
  it): a fluid column capped at `--max-width`, `flex`/`flex-wrap` rows, and a
  `@media (max-width: 40rem)` block that collapses the nav into a CSS-only burger
  menu. Mirror that pattern if you keep it — or roll your own. Either way,
  sanity-check narrow widths before calling a change done.
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
