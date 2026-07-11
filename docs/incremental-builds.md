# Incremental builds

`ctf build` is incremental: after the first build it re-renders only what changed. This page explains how, for when you want to understand the behavior — or trust it.

## What you see

The first build in a fresh site renders everything. Subsequent builds render only the pages affected by your edits: change one post's body and that one page is rewritten, while its listing pages, other posts, and the home page are left untouched. The dev server (`ctf serve`) uses the same machinery, which is why saves feel instant.

Nothing is required to opt in. Build normally and it's incremental; pass `--force` (or `--clean`) to ignore the cache and rebuild from scratch.

## How it works

After each build, cuttlefish writes a manifest to `.ctf/cache.json` recording what the build looked like:

- a hash of the effective configuration,
- a content hash per source file,
- a hash of each template plus the templates it references,
- a hash of each static file,
- a fingerprint for each aggregate (index, taxonomy, and home page).

The next build compares the current state against that manifest and re-renders only what differs. Deleting the manifest, or running `--force`, makes everything count as changed.

### One build path, two modes

There is a single build routine. An incremental build runs it against the previous manifest; a full build clears `public/` and runs the *same* routine against an empty manifest — so every page registers as changed and is rebuilt. Full builds aren't a separate code path; they're the incremental path with a blank slate. That's deliberate: the two modes can't drift apart, and the test suite asserts that a sequence of incremental builds is byte-for-byte identical to a forced full build.

### Templates propagate

Template changes follow their dependencies. cuttlefish tracks `{% extends %}` and `{% include %}` edges, so editing `base.html` invalidates every template that extends it — and every page those templates render — while editing a single leaf template only touches its own pages.

### Why listings survive body edits

This is the load-bearing detail. Listing pages (indexes, taxonomy pages, the home page) render **summaries** of content, never the body — see [the summary rule](templates.md#the-summary-rule). Each listing carries a *fingerprint* computed over exactly the summary data it shows: title, date, description, slug, url, taxonomies, and draft status. Crucially, that fingerprint never includes the body.

So when you edit a post's body, its summary fingerprint is unchanged, and every listing that shows it is correctly skipped. A listing rebuilds only when a fingerprint it depends on changes — a retitled post, a new tag, a removed item — or when its template is affected. This is why the summary/body split in templates isn't just tidiness; it's what makes "edit a body, rebuild one page" provably correct.

### Cleaning up

The manifest also drives deletion. Outputs that existed in the previous build but not the current one — a deleted post, a renamed slug, a term that lost its last item — are removed from `public/`, and directories left empty are cleaned up. A full build clears `public/` up front and prunes against the empty manifest, so the same logic covers both modes.

## When to force a full build

Incremental builds are correct for edits to content, templates, config, and static files. Reach for `--force` when something *outside* that model changes — you've upgraded cuttlefish and want to be sure, or you've been editing `public/` by hand (you shouldn't) and want a clean slate. Otherwise, the plain `ctf build` is both faster and safe.
