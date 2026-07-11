# cuttlefish

**Describe your site. An agent builds it.**

cuttlefish is an agentic static site generator for personal sites and portfolios — you write the content, agents handle the look and layout.

It has the building blocks you'd expect from a static site generator — content types, taxonomies, templates — and one deliberate omission: there's no theme to install, no CSS framework, and no asset pipeline. Your whole site is a handful of plain-text files and one stylesheet you never open by hand.

Want a minimal layout with a teal accent? A two-column projects grid? Bigger headings? Describe it, and a coding agent edits the files to match. The look of your site is something you talk your way into, not something you hand-tune.

## The mental model

A cuttlefish site is just files: a `config.toml`, your Markdown content, a few Jinja2 templates, and one stylesheet. There's nothing generated behind your back and no hidden theme layer — what's on disk *is* the site.

Because it's all plain text, two kinds of editing meet in the same place:

- **You** write the content — Markdown posts and pages, with a little TOML front matter at the top.
- **An agent** shapes everything else — the config, the templates, the CSS — in response to what you ask for.

You review the result as a diff, not as a config dialect you had to learn.

## What `AGENTS.md` is

Every site scaffolded by cuttlefish ships an `AGENTS.md` at its root. It's the agent's source of truth: the file map, the `config.toml` schema, the templating rules, and the styling conventions — everything a coding agent needs to edit *your* site correctly.

Point an agent at it and say what you want —

> Give the site a teal accent, put projects in a two-column grid, and make the headings bigger.

— and it edits the config, templates, and stylesheet to match. There are no theme docs or class names for you to memorize; the contract lives in the file, and the agent reads it.

These docs are the human-facing companion to that file. `AGENTS.md` is the compressed version an agent works from; the pages here are the full, prose reference — the same schema and rules, explained for you.

## When to use cuttlefish

It's a good fit when:

- You want a personal site, blog, or portfolio that's plain files you own, with no framework to keep up with.
- You'd rather describe changes in plain language than hand-edit CSS and templates.
- You already work with a coding agent, or you're happy to.

It's probably the wrong tool when:

- You need a large content site with plugins, shortcodes, and a theme ecosystem — reach for a batteries-included generator instead.
- You want a point-and-click visual editor. cuttlefish is text and diffs, all the way down.

## Where to next

- **[Getting started](getting-started.md)** — install it, scaffold a site, and see it live.
- **[Working with an agent](working-with-an-agent.md)** — how to ask for changes and review what comes back.
- **[Configuration](configuration.md)** — every key in `config.toml`.
- **[Deployment](deployment.md)** — get `public/` onto the web.
