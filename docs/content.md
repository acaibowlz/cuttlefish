# Authoring content

Content is the part of the site you write by hand. Each piece is a Markdown file with a small block of TOML front matter at the top.

## File layout

A content file lives at `content/<type>/<name>.md`, where `<type>` is a content type declared in `config.toml`:

```
content/
├── blog/hello-world.md      → type "blog"
├── project/riptide.md       → type "project"
└── pages/about.md           → type "pages"
```

The filename becomes the default slug: `hello-world.md` → `hello-world`. Files may be nested in subfolders; only the type folder and the filename matter.

## Front matter

Every file begins with a TOML block fenced by `+++` lines, followed by the Markdown body:

```markdown
+++
title = "Hello, World"
date = 2026-06-01
description = "A starter post."
tags = ["meta", "python"]
+++

Welcome. The body is plain **Markdown**.
```

### Required fields

For every type *except* `pages`, three fields are required:

| Field | Notes |
|-------|-------|
| `title` | The item's title. |
| `description` | One line, used in listings and metadata. |
| `date` | Publication date. **Must be an unquoted `YYYY-MM-DD` date.** |

The `date` rule is strict, and worth reading twice: it must be an unquoted TOML local date (`date = 2026-06-01`). A quoted string (`"2026-06-01"`) is rejected, and so is a date-time with a time component (`2026-06-01T09:30:00Z`). The TOML parser also validates the calendar date, so an impossible date fails the build rather than passing silently. A missing required field stops the build and names the file.

### The `pages` type is (mostly) exempt

Standalone pages (`content/pages/`) need only a `title` — no `description` and no `date`, since a page carries neither. Its slug defaults to the filename, though pages commonly set one explicitly:

```markdown
+++
title = "About"
slug = "about"
+++

This is a standalone page.
```

The [optional fields](#optional-fields) below still apply: `slug` overrides the filename-derived URL (as above) and `draft = true` hides the page from `ctf build`. What a page can't do is join a taxonomy: because it belongs to no index and no taxonomy, a configured taxonomy key (e.g. `tags`) on a page is **rejected** rather than silently ignored — it would otherwise leak the page into that taxonomy's term listings.

### Optional fields

| Field | Meaning |
|-------|---------|
| `slug` | Override the filename-derived slug. Sets the URL. |
| `draft` | `draft = true` hides the file from `ctf build`. `ctf serve` still shows it. |
| `cover` | Cover/hero image URL (e.g. `/img/post.jpg`). Unlike a custom field, it's a **summary** field, so listing templates can show a thumbnail via `item.cover` — not just the item's own page. Empty when unset. |

### Taxonomies

Add a configured taxonomy by writing its key in the front matter. The shape must match the taxonomy's `multiple` setting:

```toml
tags = ["python", "ssg"]   # multiple = true  (a list)
category = "AI"            # multiple = false (a single string)
```

A mismatch — a list where a single term is expected, or vice versa — is an error. Only configured taxonomies are recognized; see [Taxonomies](configuration.md#taxonomies).

### Custom fields {#custom-fields}

Any front-matter field that isn't a built-in (`title`, `date`, `description`, `slug`, `draft`, `cover`) or a configured taxonomy is a **custom field**. Custom fields are collected into `page.params` and made available to that item's template:

```markdown
+++
title = "Riptide"
date = 2026-05-20
description = "A tiny load-testing tool."
url = "https://github.com/you/riptide"
+++
```

Here `url` is custom, read in the template as `page.params.url`. `page.params` is the per-page counterpart to the site-wide `site.params`. Guard optional ones with `.get` — `{% if page.params.get('url') %}` — since referencing a key a given file doesn't set is otherwise an error.

A custom field can also drive ordering: point a content type's `sort_by` at it (e.g. `sort_by = "weight"`) to order the index by that field.

## Markdown

Bodies are rendered with [mistune](https://mistune.lepture.com). Alongside standard Markdown, these extensions are on:

- **Tables** (GitHub-style pipe tables)
- **Footnotes** (`[^1]`)
- **Strikethrough** (`~~text~~`)
- **Task lists** (`- [x]` / `- [ ]`)
- **Autolinks** — bare URLs become links
- **Highlight** (`==text==` → `<mark>text</mark>`)
- **Math** (`$…$` inline, `$$…$$` block)

Every `##`/`###` heading is given a stable anchor `id` derived from its text, and the headings are collected into a table of contents a template can render as `page.toc`. See [Templates & theming](templates.md#page-variables).

### Math rendering

The **Math** extension only emits markup — inline math becomes `<span class="math">\(…\)</span>` and block math `<div class="math">$$…$$</div>`. Cuttlefish ships **no** math JavaScript, so nothing renders those spans until the site adds a library itself. To turn it on, load MathJax (or KaTeX) from your base template — see the scaffold's `AGENTS.md` for a drop-in snippet. The same applies to any client-side feature (e.g. Mermaid diagrams): the generator stays JS-free, and the site opts in.

Reference images and other static assets by absolute path — `![](/img/diagram.png)` — since `static/` is copied to the site root.

## Creating a file with `ctf new`

`ctf new` writes a correctly-structured skeleton so you don't have to remember the front-matter rules:

```
ctf new blog "My First Post"
```

This creates `content/blog/my-first-post.md` with the required fields filled in (today's date, the title, a description placeholder) and any configured taxonomies listed as commented-out hints. It refuses to overwrite an existing file unless you pass `--force`. See the [CLI reference](cli.md#new) for every flag.
