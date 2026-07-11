<div align="center">

<img src="https://raw.githubusercontent.com/acaibowlz/cuttlefish/refs/heads/main/.github/cover.png" alt="cuttlefish — Agentic Static Site Generator" width="100%">

<h1>cuttlefish</h1>

<p><strong>Describe your site. An agent builds it.</strong></p>

<p>An agentic static site generator for personal sites and portfolios —<br>
you write the content, agents handle the look and layout.</p>

</div>

cuttlefish has the building blocks you'd expect from a static site generator — content types, taxonomies, templates — and one deliberate omission: there's no theme to install, no CSS framework, and no asset pipeline. Your whole site is a handful of plain-text files and one stylesheet you never open by hand.

Want a minimal layout with a teal accent? A two-column projects grid? Bigger headings? Describe it, and a coding agent edits the files to match. The look of your site is something you talk your way into, not something you hand-tune.

## How it works

Every site ships an `AGENTS.md`: the agent's source of truth for the file map, the `config.toml` schema, the templating rules, and the styling conventions. Point a coding agent at it and say what you want —

> Give the site a teal accent, put projects in a two-column grid, and make the headings bigger.

— and it edits the config, templates, and stylesheet to match. You review a diff, not a config dialect; there are no theme docs or class names to memorize. Then `ctf build` renders everything to `public/`, and `ctf serve` previews it live.

## Quick start

Requires Python 3.11+.

```
pipx install cuttlefish-ssg
ctf init my-site
cd my-site
ctf build            # render to public/
ctf serve            # live-reloading preview at http://localhost:8000
```

## Features

- **Describe, don't hand-tune:** No themes, no CSS framework, no build step — one plain stylesheet an agent edits to match what you describe.
- **Agent-first:** Every site ships an `AGENTS.md` documenting its schema and conventions, so an agent can author and style it reliably.
- **Rebuild fast:** Incremental builds cache the last render and rebuild only what changed — editing a post's body never touches your listing pages.
- **Everything else you'd expect:** Content types, taxonomies, Markdown with TOML front matter, standalone pages, pretty permalinks with pagination, a `sitemap.xml`, and a live-reloading dev server.

## Usage

| Command            | What it does                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------- |
| `ctf init <dir>`   | Scaffold a new site into `<dir>`.                                                                                    |
| `ctf build [root]` | Render the site to `public/`. Add `--force` to ignore the cache, `--drafts` to include drafts.                       |
| `ctf serve [root]` | Preview at `http://localhost:8000`, live-reloading on change. Drafts on by default; set `--port` to change the port. |

`root` defaults to the current directory, so you can run `ctf build` and `ctf serve` from inside your site.
