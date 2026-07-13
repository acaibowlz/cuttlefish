# Working with an agent

A cuttlefish site is nothing but files — `config.toml`, Markdown in `content/`, Jinja2 templates, and one stylesheet. There's no theme with hidden settings and no admin screen. You change the site by asking a coding agent for an outcome; it edits the files; you review the diff and preview. This page is about what that workflow gives you that an ordinary project doesn't.

## The agent already knows cuttlefish

What makes this work is that every scaffolded site ships an `AGENTS.md` at its root — a contract written *for the agent*. It spells out the file map, the full `config.toml` schema, the permalink tokens, every template variable, and this site's styling tokens and conventions. Agents that follow the `AGENTS.md` convention read it from the project root on their own (cuttlefish also symlinks `CLAUDE.md` to it, so Claude Code loads the same file).

The practical upshot: **you never have to explain how cuttlefish works.** You don't paste documentation, name template variables, or describe the config format. The agent arrives already knowing them, so your side of the conversation is just the outcome — "put the three most recent projects on the home page," not "iterate `recent.project` in `home.html`." It derives the second sentence from the first.

## What a conversation can change

It helps to know roughly what levers exist, so a request can name a real target instead of a vague direction. Broadly:

- **Look and feel.** Colors, fonts, spacing, and widths are CSS custom properties (`--accent`, `--font-sans`, `--max-width`, …) in `static/css/main.css`. Ask for "a warmer accent and a wider reading column" and the agent edits tokens, not scattered values. Dark mode and responsive behavior are driven by those same tokens, so they keep working through a restyle. → [Templates & theming](templates.md)
- **Layout.** The home page is assembled from sections you control — recent items per type, curated *featured* items, taxonomy term lists — and every listing and single-page template is yours to restructure. "Group blog posts by year" or "show tags as a cloud on the home page" are template changes.
- **Structure.** New content types, taxonomies, nav links, pagination, the author profile card, a custom 404 — these live in `config.toml` (plus their templates). They shape what the site *is*, so they reward being deliberate, but each is a request away. → [Configuration](configuration.md)
- **Custom values.** Anything site-wide that isn't a built-in setting goes in the free-form `[params]` table and is read in templates — an analytics ID, a feature flag, a hero toggle. Per-page, front-matter fields surface as `page.params`.
- **Whole features.** Reusable additions like reading time or a comments widget come as [recipes](recipes.md) you hand the agent.

You don't need to memorize any of this to ask for something — it's the map, not a script. The [Configuration](configuration.md) and [Templates & theming](templates.md) pages hold the detail for when you want to understand a diff.

## What stays yours

One boundary is worth calling out because the agent enforces it: **your content is off-limits to it.** `AGENTS.md` instructs the agent never to create, edit, or rewrite anything under `content/` — not the Markdown bodies, not the front matter. It may *read* your posts (to see which taxonomy terms or fields exist, so it can wire up config and templates), but the words stay yours. "Restyle the blog" won't quietly reword a post.

A few other conventions keep changes coherent without you asking:

- It styles through the design tokens rather than hardcoding values — which is *why* dark mode and mobile layouts survive an edit.
- It won't invent `config.toml` keys. The config is strictly validated, so a custom value lands in `[params]` instead of a made-up field that would fail the build.
- It keeps the "Built with cuttlefish" line in the footer unless you ask otherwise.

## Reviewing and iterating

Every change is a plain-file diff — CSS, templates, TOML — with no hidden state behind it, so the diff *is* the change in full. Read it like any small edit, with two cuttlefish-specific habits:

- **Preview with `ctf serve`.** It runs a live-reloading server: the diff tells you what changed, the browser tells you whether it's right. It also shows drafts (`draft = true`) that a production `ctf build` hides, so you can review work in progress — and check a narrow window, since layouts should stay responsive.
- **Scope-check it.** A one-line accent tweak shouldn't also touch the nav. If a change spread wider than you wanted, say so — "keep the accent, revert the nav change" is a fine next message. It's all files, so nothing is hard to undo.

Small, named steps review better than one sweeping redesign, and the incremental build keeps each step cheap — only what you changed re-renders.
