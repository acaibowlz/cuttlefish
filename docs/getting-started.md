# Getting started

## Install

cuttlefish requires **Python 3.11+**. Install it with [pipx](https://pipx.pypa.io) so the `ctf` command lands on your PATH in its own environment:

```
pipx install cuttlefish-ssg
```

The package is `cuttlefish-ssg`; the command it installs is `ctf`.

## Scaffold a site

```
ctf init my-site
cd my-site
```

`ctf init` copies a complete starter site into `my-site/` — a working `config.toml`, a handful of templates, one stylesheet, some placeholder content, and the `AGENTS.md` an agent will read. It's a real site from the first second; there's nothing to wire up.

If the target directory already has files in it, `ctf init` stops rather than clobber them. Pass `--force` to scaffold anyway.

## See it live

```
ctf serve
```

This starts a live-reloading dev server at [http://localhost:8000](http://localhost:8000). Edit a file, save, and the browser refreshes on its own. The dev server shows drafts by default and previews the site at the local root, so you don't have to think about hosting paths while you work.

When you're ready to publish, render the site to static files:

```
ctf build
```

Everything lands in `public/` — plain HTML, CSS, and a `sitemap.xml` and `robots.txt`, ready to upload anywhere. See [Deployment](deployment.md) for getting it onto the web.

## The project layout

Here's what `ctf init` gives you:

```
my-site/
├── config.toml          # the whole site's configuration
├── AGENTS.md            # the agent's contract for editing this site
├── content/             # your Markdown, one folder per content type
│   ├── blog/
│   ├── project/
│   └── pages/
├── templates/           # Jinja2 templates
│   ├── base.html
│   ├── blog.html
│   └── ...
└── static/              # copied verbatim to the site root
    └── css/main.css     # the single stylesheet
```

Two of these are yours to write directly:

- **`content/`** holds your posts and pages as Markdown with a little TOML front matter. Each subfolder is a *content type* (`blog`, `project`, `pages`), declared in `config.toml`. See [Authoring content](content.md).
- **`config.toml`** is the site's dial board — its title, URL, content types, navigation, and author details. You can edit the simple bits (title, nav labels) by hand, or let an agent handle the rest. See [Configuration](configuration.md).

The other two — `templates/` and `static/css/main.css` — are the look of the site. You *can* edit them, but they're where an agent does its best work. Which is the next page.

## Next steps

- **[Working with an agent](working-with-an-agent.md)** — describe a change and review the diff.
- **[Authoring content](content.md)** — write your first real post.
- **[CLI reference](cli.md)** — every command and flag.
