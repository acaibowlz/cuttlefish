# Configuration

The whole site is configured by a single `config.toml` at its root. This page documents every key.

## How validation works

`config.toml` is strictly validated. An unknown key is an **error**, not a silent no-op — the build stops and names the offending key, with a "did you mean…?" suggestion when one is close. This is deliberate: a mistyped key that's quietly ignored is the worst way for a config to fail, especially one an agent edits.

The single exception is the `[params]` table, whose keys are intentionally free-form (see [Custom values](#custom-values-params)).

## Top-level keys

```toml
title = "Demo Site"
base_url = "https://example.com"
```

| Key | Meaning |
|-----|---------|
| `title` | The site name. Available to every template as `site.title`. Defaults to `"Untitled Site"`. |
| `base_url` | The site's public URL. Sets absolute links in `sitemap.xml`, and its path component becomes the prefix for internal links (see [Deployment](deployment.md)). |

The remaining configuration lives in tables: `[content_types.*]`, `[taxonomies.*]`, `[home]`, `[nav]`, `[profile]`, and `[params]`.

## Content types

A content type is a category of content with its own templates and URL scheme. Each maps to a folder under `content/` — `[content_types.blog]` reads `content/blog/*.md`.

```toml
[content_types.blog]
template = "blog.html"
index_template = "blog.index.html"
permalink = "/blog/{slug}/"
index_permalink = "/blog/"
paginate = 10
sort_by = "date"
order = "desc"
```

| Key | Required | Default | Meaning |
|-----|----------|---------|---------|
| `template` | yes | — | Template for a single item of this type. |
| `permalink` | yes | — | URL pattern for a single item. See [permalink tokens](templates.md#permalink-tokens). |
| `index_template` | no | — | Template for the type's index (listing) page. |
| `index_permalink` | no | — | URL of the index page. |
| `paginate` | no | `0` | Items per index page; `0` (or omitted) disables pagination. Must be a non-negative integer. |
| `sort_by` | no | `"date"` | Front-matter field to sort the index by. Any field works, including a [custom one](content.md#custom-fields). |
| `order` | no | `"desc"` | `"desc"` (newest/largest first) or `"asc"`. |

`index_template` and `index_permalink` travel together: define both to get an index page, or neither for a type that has individual pages but no listing.

### The `pages` type

`pages` is a reserved type for standalone pages — an about page, a colophon — that belong to no index and no taxonomy.

```toml
[content_types.pages]
template = "page.html"
permalink = "/{slug}/"
```

It takes only `template` and `permalink`. Declaring `index_template` or `index_permalink` on it is an error. Content in `content/pages/` needs only a `title` and may not use taxonomies (see [Authoring content](content.md)).

## Taxonomies

A taxonomy is a user-defined classification — tags, categories — applied by adding terms to a content file's front matter.

```toml
[taxonomies.tags]
template = "taxonomy.html"
index_template = "taxonomy.index.html"
permalink = "/tags/{term}/"
index_permalink = "/tags/"
multiple = true
sort_by = "count"
order = "desc"
home = true
```

| Key | Required | Default | Meaning |
|-----|----------|---------|---------|
| `template` | yes | — | Template for a single term's page (the items tagged with it). |
| `permalink` | yes | — | URL pattern for a term page; use the `{term}` token. |
| `index_template` | no | — | Template for the taxonomy index (all terms). |
| `index_permalink` | no | — | URL of the taxonomy index. |
| `multiple` | no | `true` | Front-matter shape: `true` expects a list (`tags = ["a", "b"]`); `false` expects a single string (`category = "AI"`). |
| `sort_by` | no | `"name"` | Term ordering: `"name"` (alphabetical) or `"count"` (most-used first). |
| `order` | no | `"asc"` | `"asc"` or `"desc"`. Applies to `sort_by`. |
| `home` | no | `false` | When `true`, the home template receives this taxonomy's terms as `taxonomies.<name>`. |

## Home

The landing page.

```toml
[home]
template = "home.html"
recent = { blog = 5, project = 3 }
```

| Key | Meaning |
|-----|---------|
| `template` | Required. The landing-page template. |
| `recent` | A `content-type = count` table. The template receives each as `recent.<type>` — the newest *count* items of that type. |

Every content type `recent` references must exist.

## Navigation

The site nav bar. `labels` and `links` are two arrays paired by position, so they **must be the same length**.

```toml
[nav]
enabled = true
labels = ["Blog", "Projects", "Tags", "About"]
links  = ["/blog/", "/projects/", "/tags/", "/about/"]
```

Templates read the paired result as `site.nav`, a list of items with `.label` and `.link`. Set `enabled = false` to hide the nav without deleting its entries.

## Profile

Author/owner details, exposed to every template as `site.profile`.

```toml
[profile]
name = "Demo User"
bio = "A line or two about who you are."
avatar = "/img/avatar.svg"
email = "you@example.com"
socials = { github = "https://github.com/you", mastodon = "https://mastodon.social/@you" }
```

`avatar` is a path under `static/`. `socials` maps a platform key to its URL and keeps its written order, so links render in order and the key is available for icon or label lookup. Every field is optional.

## Custom values (`[params]`) {#custom-values-params}

`[params]` is the one table whose keys are **not** validated — the escape hatch for arbitrary site-wide values.

```toml
[params]
accent       = "teal"
show_sidebar = true
analytics_id = "UA-123"
```

Read them in any template as `site.params.<key>`, e.g. `{{ site.params.accent }}` or `{% if site.params.show_sidebar %}`. For *per-page* custom values, use front matter and `page.params` instead — see [Custom fields](content.md#custom-fields).

The raw parsed config is also available to templates as `site.config`, if a template needs a value no dedicated variable exposes.
