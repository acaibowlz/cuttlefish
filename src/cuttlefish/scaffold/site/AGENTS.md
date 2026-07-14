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
| `recipes/*.md` | Recipes to apply (if present) — read and apply when asked; not published. | 📖 |
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

## Recipes

A **recipe** is a short Markdown guide for adding one feature (reading time, a
breadcrumb trail, comments, …). A fresh site has none; the author copies the ones
they want from cuttlefish's recipe library into a `recipes/` folder here.
*Placing* a recipe doesn't apply it — you apply one when asked.

**When the user asks for a feature, check `recipes/` first.** If the folder
exists, scan the descriptions (`grep -h '^description' recipes/*.md`) — each
recipe's front matter is just its `name` and one-line `description`. If one
matches, read that file and apply it: follow its **How** steps and honor its
**Where** and **When**. If nothing matches (or there is no `recipes/` folder),
build the feature directly using the rest of this guide. Once applied, the feature
lives in the templates, CSS, and config you edited — not in the recipe file;
leaving it in `recipes/` (or deleting it) has no effect on the build.

Recipes are **additive** by rule: they edit templates, CSS, and — for custom
site-wide values — the free-form `[params]` table, and nothing else. They do
**not** edit the structural config tables (`content_types`, `taxonomies`, `nav`)
that define the site; a recipe that needs one names it as a prerequisite. They
prefer build-time solutions over client-side JavaScript, which (when genuinely
needed) is an opt-in file under `static/js/` loaded by a `<script>`, the same
pattern as the math and diagram scripts under *Content format*. If no recipe
covers the request, build it directly using the rest of this guide.

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

The site author block on the home page is rendered from `[profile]` (see below)
via the site-wide `site.profile` global, so the home template gates it on
`{% if site.profile %}` — no `[home]` key controls it.

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
`alt` should default to the name. The home template renders it as an author card
via `site.profile`; being site-wide, it's available on every page.

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

### Custom values (`[params]`)

```toml
[params]
accent       = "teal"
show_sidebar = true
analytics_id = "UA-123"
```

The **only** table whose keys are not validated. Every other table rejects
unknown keys as typos; `[params]` is the escape hatch for arbitrary site-wide
values. Read them in any template as `site.params.<key>` (e.g.
`{% if site.params.show_sidebar %}` or `{{ site.params.accent }}`). For
**per-page** custom values, add them to a page's front matter instead and read
them off `page.params` — the per-page counterpart to `site.params`. It holds
every front-matter field that is not a built-in (`title`, `date`,
`description`, `slug`, `draft`, `featured`) or a configured taxonomy. Guard
optional ones with `.get`, since a missing key otherwise errors (e.g.
`{% if page.params.get('hero_layout') %}{{ page.params.hero_layout }}{% endif %}`).

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
featured = true            # optional; content types only — feeds home [home].featured
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

**Markdown body extensions.** Beyond standard Markdown, bodies support tables,
footnotes (`[^1]`), strikethrough (`~~x~~`), task lists (`- [x]`), autolinks,
highlight (`==x==` → `<mark>`), and math (`$…$` inline, `$$…$$` block).

Math emits only markup (`<span class="math">\(…\)</span>` and
`<div class="math">$$…$$</div>`) — **no math JavaScript ships by default**, so it
renders as plain text until the site loads a library. If the author wants math to
render, add a MathJax script to `templates/base.html` before `</body>`:

```html
<script>
  window.MathJax = { tex: { inlineMath: [['\\(', '\\)']], displayMath: [['$$', '$$']] } };
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
```

The same pattern (a script the template loads, opt-in) covers any client-side
feature, e.g. Mermaid diagrams from ```mermaid``` code blocks.

## Permalink tokens

Usable in any `permalink`/`index_permalink`: `{slug}`, `{type}`, `{year}`,
`{month}`, `{day}` (from `date`), `{term}`, `{taxonomy}`.

## Theming & templates

Templates are Jinja2 and live in `templates/`. `base.html` is the shared layout;
others `{% extends "base.html" %}`. A global `site` object is available
everywhere: `site.title`, `site.base_url`, `site.nav`, `site.profile`,
`site.params` (your free-form `[params]` table), and `site.config` (the raw
parsed `config.toml`).

Variables per template kind:

| Template | Variables |
|----------|-----------|
| single content (`blog.html`) | `page` / `item` (full, incl. `page.body_html`, `page.toc`, and `page.params` free-form fields), `type`, `terms` |
| type index (`blog.index.html`) | `items` (summary only), `page` (pagination), `type` |
| taxonomy term (`taxonomy.html`) | `taxonomy`, `term`, `items` (summary only) |
| taxonomy index (`taxonomy.index.html`) | `taxonomy`, `terms` |
| home (`home.html`) | `recent` and `featured` — maps of content-type → summary-only items (`recent.blog`, `featured.blog`); `taxonomies` — map of taxonomy → terms with `name`/`count`/`url` (`taxonomies.tags`). Author details come from `site.profile` (on every page), not a home-only variable. |

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

### The 404 page

`templates/404.html` is special: it renders straight to `public/404.html` (no
content file, no permalink), and static hosts serve it for any missing path.
It gets the global `site` context only — there is no `page` — so extend
`base.html` and use `site.*`. Keep its links **root-absolute** (`/`, `/blog/`),
since it can be served for a URL at any depth. Delete the template and no 404 is
emitted; it never appears in `sitemap.xml`.

### Styling

Styling is **plain CSS** in `static/css/main.css`, linked once from `base.html`.
There is no asset pipeline and no CSS framework: `static/` is copied verbatim,
so whatever you write ships as-is. Follow these conventions so the site stays
consistent as you edit it:

- **Use the design tokens, don't hardcode.** Colors, fonts, and layout are CSS
  custom properties on `:root`: surfaces (`--bg`, `--surface`, `--border`), text
  (`--fg`, `--muted`), accent (`--accent`, `--accent-hover`), typography
  (`--font-sans`, `--font-mono`), and width/shape (`--max-width`, `--width-wide`,
  `--radius`). Reference them with `var(--accent)` rather than repeating raw
  values. Need a new color or spacing value site-wide? Add a token to `:root` and
  use it everywhere, instead of sprinkling literals.
- **Understand the layout container.** `.container` caps and centers content at
  `--max-width` — the reading column (`44rem`). The home page opts into the wider
  `--width-wide` with `{% block body_class %}layout-wide{% endblock %}` (the
  `body.layout-wide` rule swaps the width) to fit its two-column layout; do the
  same for any full-width page. The `.site-header`/`.site-footer` backgrounds are
  full-bleed (span the viewport) while their inner `.container` is width-capped;
  that inner frame is pinned to `--width-wide` so the nav bar stays put across
  pages. `main` is a `.container` itself.
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
- **Keep the cuttlefish attribution.** Always include a `Built with cuttlefish
  (https://github.com/acaibowlz/cuttlefish)` line in the site footer — it ships
  in `base.html`'s `<footer>` by default. Preserve it when you restyle or
  restructure the footer, and only remove it if the user explicitly asks you to.
- **Don't reach for a CSS framework by default.** You write clean CSS as easily
  as utility classes, and a framework (Tailwind, etc.) would mean a build step
  this project deliberately doesn't have. If the user explicitly wants one, treat
  it as an opt-in they've chosen — not the default.
