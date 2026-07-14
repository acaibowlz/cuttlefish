# Recipes

A library of ready-to-apply feature guides for cuttlefish sites. Each recipe is a
self-contained Markdown file that tells a coding agent how to add **one** feature
to a site by editing its templates, CSS, and `[params]` — there is no plugin
system and no build step.

These are **examples to copy from**. They are not shipped inside a generated site
or installed with the `cuttlefish-ssg` package; they live here in the repo so you
can browse them and pull in the ones you want.

## Using a recipe

Pick one below and copy it into your site's `recipes/` folder (create it if it
isn't there), then ask your agent to apply it. The agent reads the recipe from
`recipes/` and makes the edits — an ordinary diff (templates / CSS /
`config.toml`) you review like any other change. Placing the file doesn't apply
it on its own; you ask.

The `recipes/` folder isn't published (the build ignores it), so it just records
the recipes your site uses. To update an applied one, replace the file with the
newer version and re-apply.

## Available recipes

| Recipe | What it does |
|--------|--------------|
| [`reading-time`](reading-time.md) | Estimated reading time on single article pages (build-time, no JS). |
| [`breadcrumb`](breadcrumb.md) | A breadcrumb trail (Home / Section / Page) on content pages. |

## Writing a recipe

A recipe is a Markdown file with `+++` TOML front matter and a fixed body.

```
+++
name = "reading-time"
description = "One line — this is the index used to browse and match recipes."
+++
```

The body covers **what · where · when · how**: what it does, where it applies
(which pages and which files), when to use or skip it, and how — the numbered
steps, each naming the exact file and snippet, ending with a quick verify. Keep it
light; fold limits and caveats into a line rather than a separate heading.

Two rules keep recipes portable, additive add-ons rather than a plugin system:

- **Additive surfaces only.** A recipe edits templates, CSS, optional client-side
  JS, and custom values under the free-form `[params]` table — and nothing else.
  It must **not** edit the structural config tables (`content_types`,
  `taxonomies`, `nav`) that define the site; when a feature depends on one, name
  it as a *prerequisite* rather than editing it.
- **Prefer build-time.** Solve it in the template/config/CSS where you can. Ship
  client-side JS only when the feature genuinely needs it, as an opt-in file
  under `static/js/` loaded by a `<script>` (the same pattern as the math and
  diagram scripts in the site's `AGENTS.md`).
