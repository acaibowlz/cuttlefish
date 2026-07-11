# Working with an agent

The look and structure of a cuttlefish site — its config, templates, and CSS — is meant to be edited by a coding agent, in response to what you ask for in plain language. You describe the change; the agent edits the files; you review a diff. This page is about doing that well.

## What `AGENTS.md` is

Every scaffolded site has an `AGENTS.md` at its root. It's a briefing document written *for the agent*: the file map, the `config.toml` schema, the templating rules, the permalink tokens, and the styling conventions specific to this site. It's why an agent can make a coherent change without you explaining how cuttlefish works first.

You don't have to do anything to "load" it. Coding agents that follow the `AGENTS.md` convention pick it up from the project root on their own. (cuttlefish also drops a `CLAUDE.md` symlink pointing at it, so Claude Code reads the same file.)

Your job isn't to know what's in `AGENTS.md` — it's to describe what you want. The agent reads the contract; you describe the outcome.

## How to ask

The agent is good at turning an outcome into file edits. It's less good at reading your mind. The more your request names a concrete result, the better the diff.

A request that works well:

> Give the site a teal accent, put projects in a two-column grid, and make the headings a bit bigger.

Each part maps to a real edit — the accent token in `main.css`, the projects index layout, the heading scale — so the agent can act on it directly.

A request that leaves too much open:

> Make it look nicer.

"Nicer" has no target. You'll get *a* change, but probably not *your* change. If you're not sure what you want, it's fine to say so and ask for options — just make the ask explicit ("show me two header layouts") rather than vague.

Some things worth naming when they matter to you:

- **Where** — "on the home page", "in the post footer", "only on project pages".
- **How much** — "a bit bigger", "much tighter spacing", "just the accent, nothing else".
- **What not to touch** — "leave the blog layout alone" keeps a change from spreading.

## Reviewing what comes back

Because a cuttlefish site is plain files, every change is a readable diff — CSS, templates, and TOML, not a theme's internal settings. Read it the way you'd read any small edit:

- **Does it match what you asked?** The change should be scoped to your request. A one-line accent tweak shouldn't also rewrite the nav.
- **Preview it.** Run `ctf serve` and look. The diff tells you what changed; the browser tells you whether it's right. Check a narrow window too — the starter theme is responsive, and changes should stay that way.
- **Iterate in small steps.** "Now make the grid three columns on wide screens" is easier to review than a fresh from-scratch redesign each time.

If a change went wider than you wanted, say so — "revert the nav change but keep the accent" is a perfectly good next message.

## What agents handle vs. what you write

A clean division of labor keeps things predictable:

- **You write content** — the Markdown in `content/`, and the simple front-matter fields on it. That's yours; an agent generally shouldn't be rewriting your posts.
- **The agent shapes everything else** — `config.toml`, the templates, and `main.css`. That's where the "describe it" workflow shines, and where `AGENTS.md` gives the agent the rules to work within.

For the details an agent works from — the config schema, the template variables, the styling tokens — the same material is written up for you in [Configuration](configuration.md), [Templates & theming](templates.md), and the rest of these docs. You rarely need it to make a request, but it's there when you want to understand a diff.
