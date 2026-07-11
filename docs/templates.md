# Templates & theming

Templates turn parsed content into HTML; the stylesheet gives it a look. Both are plain files an agent edits well — but here's how they work, for when you want to read a diff or make a change yourself.

## Templates

Templates are [Jinja2](https://jinja.palletsprojects.com) and live in `templates/`. `base.html` is the shared layout; the others extend it:

```jinja
{% extends "base.html" %}
{% block content %}
  <h1>{{ page.title }}</h1>
  <div class="body">{{ page.body_html | safe }}</div>
{% endblock %}
```

Two settings shape how templates behave:

- **Autoescape is on.** Output is HTML-escaped by default; rendered Markdown bodies are marked safe explicitly with `| safe`.
- **Undefined is strict.** Referencing a variable — or a dict key — that doesn't exist raises an error rather than rendering blank. This catches typos, but it means optional values must be guarded: `{% if page.params.get('url') %}`, not `{% if page.params.url %}`.

## The global `site` object

Available in every template:

| Variable | What it is |
|----------|-----------|
| `site.title` | The site name. |
| `site.base_url` | The configured public URL. |
| `site.nav` | The nav entries — a list of items with `.label` and `.link`. |
| `site.profile` | Author details: `.name`, `.bio`, `.avatar`, `.email`, `.socials`. |
| `site.params` | The free-form `[params]` table. |
| `site.config` | The raw parsed `config.toml`, as a fallback. |

## Variables by template kind

Each template kind receives a different context. The most important distinction is **full items vs. summaries** — see [the summary rule](#the-summary-rule) below.

| Template | Configured by | Receives |
|----------|---------------|----------|
| Single content (`blog.html`) | `content_types.<t>.template` | `page` / `item` (full), `type`, `terms` |
| Type index (`blog.index.html`) | `content_types.<t>.index_template` | `items` (summaries), `page` (pagination), `type` |
| Taxonomy term (`taxonomy.html`) | `taxonomies.<t>.template` | `taxonomy`, `term`, `items` (summaries) |
| Taxonomy index (`taxonomy.index.html`) | `taxonomies.<t>.index_template` | `taxonomy`, `terms` |
| Home (`home.html`) | `home.template` | `recent.<type>`, `featured.<type>`, `taxonomies.<name>` |

On the home page, `recent.blog` and `featured.blog` are lists of summaries; `taxonomies.tags` is a list of terms (each with `name`, `count`, `url`) for any taxonomy configured with `home = true`. Author details come from `site.profile`, available everywhere.

### Page variables (single content) {#page-variables}

Single-content and page templates get the full item as `page` (also aliased `item`):

- `page.title`, `page.date`, `page.description`, `page.slug`, `page.url`, `page.draft`, `page.featured`
- `page.body_html` — the rendered Markdown body (use `| safe`)
- `page.taxonomies` — a map of taxonomy name to the item's terms
- `page.params` — the item's [custom fields](content.md#custom-fields)
- `page.toc` — the body's headings, in order, each with `level` (1–6), `text`, `id`, and `url` (the `#id` anchor). Empty when the body has no headings.
- `terms` — a map of taxonomy name to `{name, url}` objects, so content can link each term to its term page

### The summary rule {#the-summary-rule}

Listing templates — every index, taxonomy term, taxonomy index, and the home page — receive **summaries**, not full items. A summary carries only:

> `title`, `date`, `description`, `slug`, `url`, `taxonomies`, `draft`

It deliberately omits `body_html`. This isn't only tidiness: it's what keeps [incremental builds](incremental-builds.md) correct. Because no listing can render a body, editing a post's body provably can't change any listing, so listings are skipped on a body-only edit. A single-content template can render the body; a listing template cannot.

## Permalink tokens {#permalink-tokens}

`permalink` and `index_permalink` patterns are substituted with these tokens:

| Token | From |
|-------|------|
| `{slug}` | The item's slug |
| `{type}` | The content type name |
| `{year}` `{month}` `{day}` | The item's `date` |
| `{term}` | A taxonomy term |
| `{taxonomy}` | A taxonomy name |

A pattern that ends in `/` produces a pretty URL: `/blog/{slug}/` → `/blog/my-post/`, written to `public/blog/my-post/index.html`. A pattern ending in a filename (`.xml`, `.html`) is written as that file.

## Styling

Styling is plain CSS in `static/css/main.css`, linked once from `base.html`. There's no asset pipeline and no framework — `static/` is copied verbatim, so what you write ships as-is. The starter stylesheet follows a few conventions worth keeping:

- **Design tokens on `:root`.** Colors, fonts, and sizing are CSS custom properties: surfaces (`--bg`, `--surface`, `--border`), text (`--fg`, `--muted`), accent (`--accent`, `--accent-hover`), typography (`--font-sans`, `--font-mono`), and shape (`--max-width`, `--radius`, `--radius-sm`). Reference them with `var(--accent)` rather than hardcoding values; add a token for anything you want to reuse.
- **Dark mode for free.** The palette is themed with a `@media (prefers-color-scheme: dark)` block that overrides the same tokens. Style through tokens and light/dark both work.
- **Mobile-first and responsive.** Size layout in relative units (`rem`/`%`/`ch`) or `clamp()`, let content reflow, and scale images with `max-width: 100%`. The starter caps a fluid column at `--max-width` and collapses the nav into a CSS-only menu under `40rem`.
- **Semantic classes.** Style by meaning (`.post-list`, `.site-header`) rather than utility classes or inline styles, and keep a class and its rule in the same edit.

Because everything flows from tokens, "give the site a teal accent" is usually a one-line change — the accent token — not a sweep through the file. That's what makes the [agent workflow](working-with-an-agent.md) feel light.
