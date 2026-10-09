# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.12] - 2026-10-09

### Added

- `ctf build` and `ctf serve` take `--verbose` / `-v` to list the files behind
  each count in the build report.

### Changed

- Build output reads as one noun per line: "3 static files" (was "copied").
- Removed files are reported as "− 2 removed"; the paths are listed only with
  `--verbose`.
- The `ctf serve` banner aligns its lines and shows the watched path as given on
  the command line, naming the folder when that is just `.`.

## [0.1.11] - 2026-10-03

### Changed

- Build output lists removed files by URL and drops the "x of y" page counts.

## [0.1.10] - 2026-10-03

### Added

- `ctf update` replaces a site's `AGENTS.md` with the guide for the installed
  version, keeping a differing copy as `AGENTS.md.bak`.
- Scaffold: `CUSTOMIZATION.md` holds site-specific agent instructions;
  `AGENTS.md` is marked protected and points the agent there.

### Changed

- Build output colors only the counts; numbers or words like `True` in the site
  title are no longer recolored. The 404 line reads `404.html`.

### Removed

- `ctf init` no longer symlinks `CLAUDE.md` to `AGENTS.md`.

## [0.1.9] - 2026-10-03

### Fixed

- Errors are reported as `error:` diagnostics instead of Python tracebacks or
  internals: non-UTF-8 files (with file and line), file-system errors (unreadable
  files, `public` being a file), mixed-type `sort_by` values, a non-table
  `content_types`/`taxonomies`, a busy `ctf serve` port, and a broken `$EDITOR`
  for `ctf new --edit` (which now also accepts arguments, e.g. `code -w`).
- Template errors name the template file and line, show the failing expression
  (`'site' has no attribute 'feeds'`) instead of a Python class, and report a
  missing template without the absolute search path.
- Two sources resolving to one URL (posts sharing a slug, a page shadowing a
  listing, tags that slugify alike) fail the build instead of one silently
  overwriting the other.
- A `slug` or permalink containing `..` can no longer write outside `public/`,
  and pruning never deletes outside it.
- `ctf serve` binds its port before the first build, so a busy port no longer
  leaves a preview build (drafts, no subpath prefix) in `public/`.
- `ctf serve` live reload works for a site stored under a folder named `public`
  (it ignored every change), and no longer rebuilds on unrelated changes when the
  site is under a folder named `content`, `templates` or `static`.

### Changed

- `ctf serve` watches the whole site (except `public/` and hidden files) and
  reloads the browser only when the output changed.
- Build output lists the sitemap and robots.txt on their own lines and drops
  "updated" (`RSS feed`, `404 page`).
- Front matter is type-checked instead of coerced: `title`, `description`,
  `cover` and `slug` must be strings and `draft` a boolean (`draft = "no"` used
  to hide the post). An explicit `slug` must be URL-safe (letters, digits, `-`,
  `_`). In `config.toml`, `title`, `description` and `base_url` must be strings,
  and an unmatched `{`/`}` in a permalink is rejected.

## [0.1.8] - 2026-10-03

### Added

- `ctf --version` (`-V`).

## [0.1.7] - 2026-10-03

### Added

- `lang` config key (default `"en"`) and per-item `lang` front matter; sets
  `<html lang>` and the feed's `<language>`.
- `description` config key, used as the feed's channel description.
- Optional `updated` front-matter date, emitted as `<lastmod>` in `sitemap.xml`.
- Feed items carry their content type as `<category>`.

### Changed

- **Breaking:** one site-wide RSS feed at `/feed.xml` replaces per-type feeds;
  `feed = true` now adds a type to it. `site.feeds` is replaced by `site.feed`.
- Build output is split into one line per kind of output, shown only when
  something changed.

## [0.1.6] - 2026-07-26

### Changed

- Scaffold: posts without headings use the `.panel-grid` layout too, so the
  article no longer shifts between posts.
- Scaffold: teaching comments removed from the starter templates and stylesheet;
  `AGENTS.md` and the docs cover the contract.

## [0.1.5] - 2026-07-26

### Changed

- Scaffold: index, taxonomy and page templates use the `.panel-grid` layout, so
  content and nav stay aligned across pages.

### Fixed

- `ctf serve` no longer 404s on non-ASCII slugs.
- `sitemap.xml` and RSS feeds percent-encode their URLs.

### Documented

- Slugs keep letters from any script; there is no transliteration.

## [0.1.4] - 2026-07-19

### Added

- RSS feeds: `feed = true` on a content type publishes a summary feed at
  `<index_permalink>feed.xml`, advertised via `site.feeds`.

## [0.1.3] - 2026-07-19

### Changed

- Scaffold: home and blog posts use a full-height side panel (profile and tags
  on home, table of contents on posts) instead of the floating-card sidebar.

## [0.1.2] - 2026-07-16

### Added

- `ctf check`: validates the site without writing anything.
- `robots.txt` generated when `base_url` is set; `static/robots.txt` overrides it.
- `item.type` on listing summaries.
- Optional `cover` front-matter field, available on listings as `item.cover`.
- `[taxonomies.<name>.items]` sets item order on term pages (default newest
  first, previously filename order).

### Removed

- **Breaking:** the `featured` front-matter flag and `[home].featured`; use a
  taxonomy instead.

### Changed

- **Breaking:** standalone pages require a `title` and reject taxonomy keys.
- Recipes are copied into a per-site `recipes/` folder for the agent to apply.

## [0.1.1] - 2026-07-14

### Added

- PyPI project URLs.
- CI test workflow with coverage and README badges.

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

[0.1.12]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.11...v0.1.12
[0.1.11]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.10...v0.1.11
[0.1.10]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.9...v0.1.10
[0.1.9]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/acaibowlz/cuttlefish/releases/tag/v0.1.0
