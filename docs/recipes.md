# Recipes

A **recipe** is a short, ready-to-apply guide for adding one feature to a cuttlefish site — an estimated reading time, a breadcrumb trail, a comments widget. An agent reads the recipe and makes the change by editing your site's templates, CSS, and configuration. There's no plugin to install and nothing new runs at build time; applying a recipe just produces an ordinary diff you review like any other change.

Recipes are how cuttlefish offers reusable features without a plugin system. Because a coding agent edits your files directly, a "feature" doesn't need to ship as code — it can ship as *instructions the agent follows*.

## The recipe library

A freshly scaffolded site ships with **no recipes** — they're entirely opt-in. When you want a feature, pick the one you need from the library and apply it to your site (or hand it to your agent to apply); if nothing fits, [write your own](#writing-your-own).

The library lives in the [`recipes/` folder of the cuttlefish repository](https://github.com/acaibowlz/cuttlefish/tree/main/recipes). The starter set:

- **`reading-time`** — an estimated "N min read" on single article pages, computed at build time.
- **`breadcrumb`** — a Home / Section / Page trail on content pages.

## Using a recipe

You don't install or invoke recipes — you place one in your site and ask your agent to apply it:

1. **Browse the library** and open the recipe you want.
2. **Copy it into your site's `recipes/` folder** (create the folder if it isn't there yet). This folder isn't published — the build ignores it — so it's simply a home for the recipes your site uses. Commit it, and the folder shows at a glance which recipes your site draws on.
3. **Ask your agent to apply it.** It reads the recipe from `recipes/` and makes the edits. Placing the file doesn't apply it on its own — you ask.
4. **Review the diff** and preview with `ctf serve`, the same as any other change.

Once applied, the feature lives in the templates, CSS, and config the agent edited — not in the recipe file. You can keep the file in `recipes/` for reference or delete it; either way it doesn't affect the build, and editing it later won't change your site unless you ask for it to be re-applied. To pick up an improved recipe, replace the file with the newer version and re-apply.

## What a recipe can change

Recipes are deliberately **additive** — they layer a feature onto your site without restructuring it. A recipe may edit:

- **templates** (`templates/*.html`) and **styles** (`static/css/main.css`),
- **client-side JavaScript**, when a feature genuinely needs it, as an opt-in file under `static/js/` loaded by a `<script>` — recipes prefer to solve things at build time and reach for JS only when necessary,
- **custom site-wide values** under the free-form `[params]` table in `config.toml`.

A recipe does **not** touch the structural parts of your config — your content types, taxonomies, or nav. Those define what your site *is*, and changing them is your call, not something a drop-in feature should do. When a recipe depends on one (a gallery recipe that expects a `photos` content type, say), it names that as a prerequisite for you to set up first, rather than reconfiguring your site itself.

## Writing your own

A recipe is a plain Markdown file, so making a feature repeatable across your sites is just writing one more file. It has TOML front matter fenced by `+++` and a short, fixed body.

```
+++
name = "reading-time"
description = "Show estimated reading time on single article pages."
+++
```

The one-line `description` is what identifies the recipe when browsing the library. The body then covers four things — **what, where, when, how**:

- **What** — what it does, in a sentence.
- **Where** — which pages it affects and which files it touches (templates, CSS, `[params]`).
- **When** — when to apply it, and when to skip.
- **How** — the numbered steps, each naming the exact file and snippet, ending with a quick way to verify.

Keep it light: *what*, *where*, and *when* are usually a line each, and any limits or caveats fold into them (or a short closing note) rather than becoming headings of their own.

Keep to the two rules that make recipes portable: stay **additive** (templates, CSS, opt-in JS, and `[params]` — never the structural config tables), and **prefer build-time** solutions over client-side JavaScript. The [gallery README](https://github.com/acaibowlz/cuttlefish/tree/main/recipes) states the same rules alongside the existing recipes as worked examples.
