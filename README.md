<div align="center" style="text-align: center;">

<h1>cuttlefish — Agentic Static Site Generator</h1>

<p>
  Style your personal site / portfolio by describing it. You write the content, agents do the rest.
</p>

</div>

**cuttlefish** is just another ssg that you are already familiar with: content type, taxonomy, you name it. However, **cuttlefish** has no themes to install, no CSS framework, and no asset pipeline — just one plain stylesheet. You never have to open it. Want a minimal layout with a teal accent? A two-column projects grid? Bigger headings? You _describe_ it, and an agent edits that single file (and the templates) to match. The look and layout of your site is something you talk your way into, not something you hand-tune.

## The loop

You don't hand-edit a theme — you describe what you want, an agent edits the
files, and `ctf` builds them:

1. Point a coding agent at your site. Every site ships an `AGENTS.md` that is the
   agent's source of truth — the file map, the `config.toml` schema, the
   templating rules, and the styling conventions.
2. Just describe what you want, and the agent updates the stylesheet, templates,
   and config to match.
3. `ctf build` renders everything to `public/`. `ctf serve` previews it live.

## Quick Start

```
pipx install cuttlefish-ssg
ctf init my-site
cd my-site
ctf build            # render to public/
ctf serve            # live-reloading preview at http://localhost:8000
```

## Features

- Agent-first — a generated AGENTS.md documents the schema and conventions so an agent can author and theme the site reliably.
- Incremental builds — a build cache rebuilds only what changed; a strict summary/body split keeps listings from rebuilding when a post's body is edited.
- Live reload — ctf serve watches files and reloads the browser, drafts on by default.
