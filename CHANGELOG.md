# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.6] - 2026-07-26

### Changed

- Scaffold: a blog post with no headings now uses the same `.panel-grid` layout
  as one with a table of contents, just without the side panel — it kept the
  plain centered container before, so the article shifted sideways as you moved
  between posts in the same blog.
- Scaffold: the `{# … #}` teaching comments are gone from the starter templates.
  They explained the generator's contract inside files a user then edits and
  ships as their own site; that contract belongs in `AGENTS.md` and the docs,
  which already carry all of it. The comments in `static/css/main.css` are gone
  for the same reason — the starter files a site inherits are now unannotated.

## [0.1.5] - 2026-07-26

### Changed

- Scaffold: the content index, taxonomy term, taxonomy index and standalone page
  templates now use the same `.panel-grid` / `.panel-main` layout as the home
  page and posts. They have no side panel, but the grid reserves its width, so
  the content column and the header nav sit in the same place on every page
  instead of shifting between layouts.

### Fixed

- `ctf serve` no longer 404s on content whose slug contains non-ASCII
  characters. Browsers percent-encode those paths on the wire, so a post at
  `/blog/新貼文/` arrived as `/blog/%E6%96%B0%E8%B2%BC%E6%96%87/` and never
  matched the file on disk. The dev server now decodes the request target before
  resolving it, with the path-traversal check running on the decoded path so an
  encoded `%2e%2e` is still rejected.
- `sitemap.xml` and RSS feeds now percent-encode their URLs. `<loc>`, `<link>`
  and `<guid>` are parsed as strict ASCII URIs, so a Unicode slug previously
  produced a technically invalid document. HTML `href`s deliberately keep the
  readable form (`/blog/新貼文/`) — browsers encode those on the wire.

### Documented

- Slugs keep letters from any script, and cuttlefish does not transliterate:
  `新貼文.md` is served at `/blog/新貼文/` and `Café Crème` becomes
  `café-crème`. Only URL- and filesystem-hostile characters are stripped.
  Folding to ASCII instead would collide every non-Latin title onto one slug,
  and transliteration mangles CJK. Written up in `docs/content.md` and the
  scaffold `AGENTS.md`.

## [0.1.4] - 2026-07-19

### Added

- RSS feeds. A content type with `feed = true` publishes an RSS 2.0 feed of its
  recent posts at `<index_permalink>feed.xml` (e.g. `/blog/feed.xml`). It's a
  _summary_ feed — title, link, date and description per entry, newest 20 first —
  gated on `base_url` like the sitemap, and requires the type to have an index.
  Rendered in core (no template), it is a fingerprinted aggregate: regenerated
  only when a listed post's metadata changes, pruned when disabled, and kept out
  of `sitemap.xml`. Templates get a `site.feeds` global (each with `.type` and a
  root-relative `.url`); the scaffold `base.html` uses it to emit
  `<link rel="alternate">` autodiscovery tags, and enables the feed on `blog`.

## [0.1.3] - 2026-07-19

### Changed

- Starter theme: the home page and single blog posts now use a narrow,
  full-height side panel on the right — the author profile and tags on home, the
  table of contents on posts — with the main content centered beside it, in
  place of the earlier floating-card sidebar. The panel runs from the header to
  the footer and is hidden below the mobile breakpoint; posts with no headings
  keep the plain reading column. On these pages the nav right-aligns to the
  panel's left edge, and TOC anchors now land clear of the sticky header.
  (Scaffold-only — no change to the generator.)

## [0.1.2] - 2026-07-16

### Added

- `ctf check` command: validate config, content, and templates by running the
  full build pipeline into a throwaway directory — nothing is written to the
  site and the incremental cache is left untouched. Exits non-zero on the first
  error, for use in CI or a pre-commit hook.
- Generate `public/robots.txt` when `base_url` is set: it permits all crawlers
  and advertises the sitemap (`Sitemap: <base_url>/sitemap.xml`). A site that
  ships its own `static/robots.txt` overrides the generated one.
- Listing summaries now expose `item.type`, so listing templates can label an
  item with its content type — handy on taxonomy term pages, where a tag may
  span types. The scaffold's `taxonomy.html` renders it as a small prefix.
- Optional `cover` front-matter field (a cover/hero image URL), promoted to a
  first-class **summary** field — so listing templates can show a thumbnail via
  `item.cover`, not just the item's own page. It joins `meta_fingerprint`, so a
  cover change correctly rebuilds the aggregates that show it. Empty when unset.
- Configurable item order on taxonomy term pages via a nested
  `[taxonomies.<name>.items]` sub-table (`sort_by`/`order`). `sort_by` is
  open-ended like a content type's — any front-matter field, validated against
  real items at build time. This also **fixes** term pages previously emitting
  items in filename order; they now default to newest-first (`date` desc),
  matching a type index.

### Removed

- **Breaking:** the `featured` front-matter flag and the `[home].featured`
  config table (with its `featured.<type>` home-template variable). It duplicated
  what a taxonomy already does; use a taxonomy term instead. A leftover
  `featured` in `[home]` is now an unknown-key error.

### Changed

- **Breaking:** standalone `pages` now require a `title` and reject configured
  taxonomy keys. A page joins no taxonomy listing, so a key like `tags` was a
  silent no-op that could still leak the page into term pages; it is now a build
  error. `description` and `date` remain optional for pages.
- Recipes are used by copying them into a per-site `recipes/` folder for the
  agent to discover and apply, rather than pasting them into the conversation.
  The repo's `recipes/` gallery remains the source of examples. (Documentation
  and agent-contract only.)

## [0.1.1] - 2026-07-14

### Added

- `[project.urls]` package metadata (Homepage, Repository, Documentation) so the
  PyPI page links back to the repository and hosted docs.
- Continuous-integration test workflow with coverage reporting, plus README
  status badges.

## [0.1.0] - 2026-07-13

Initial release of **cuttlefish** — an agentic static site generator published
as `cuttlefish-ssg` with the `ctf` CLI.

### Added

- Static-site pipeline: content types, taxonomies, Jinja2 templates, and
  Markdown with TOML front matter, rendered to `public/`.
- Pretty permalinks with token substitution and pagination, standalone `pages`,
  a home page with recent/featured/taxonomy sections, an author profile, a
  configurable nav, an optional 404 template, and `sitemap.xml`.
- Incremental builds: a single build path that rebuilds only what changed, with
  a summary/body split that keeps listing pages correct.
- Strict `config.toml` validation (unknown keys rejected) with a free-form
  `[params]` escape hatch, and two-tier user-facing error messages.
- Markdown extensions (tables, footnotes, strikethrough, task lists, highlight,
  math) plus heading anchors and a table of contents.
- Subpath hosting via `base_url`, and a live-reloading dev server (`ctf serve`).
- `ctf init` scaffolds a starter site — including an `AGENTS.md` that documents
  the site-authoring contract for coding agents.
- Recipes: a gallery of copy-in feature guides (e.g. reading time, breadcrumbs).
- MIT license.

[0.1.6]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/acaibowlz/cuttlefish/releases/tag/v0.1.0
