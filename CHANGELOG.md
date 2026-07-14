# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Generate `public/robots.txt` when `base_url` is set: it permits all crawlers
  and advertises the sitemap (`Sitemap: <base_url>/sitemap.xml`). A site that
  ships its own `static/robots.txt` overrides the generated one.

### Fixed

- Reject `featured` on standalone `pages`. The flag feeds the home
  `[home].featured` sections, which pages never join, so it was silently
  ignored; setting it is now a build error.

### Changed

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

[Unreleased]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/acaibowlz/cuttlefish/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/acaibowlz/cuttlefish/releases/tag/v0.1.0
