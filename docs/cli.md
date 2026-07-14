# CLI reference

cuttlefish installs one command, `ctf`, with five subcommands. Run `ctf --help` or `ctf <command> --help` for the same information at the terminal.

## `init`

```
ctf init <directory> [--force]
```

Scaffold a new site into `<directory>` — config, templates, stylesheet, starter content, and `AGENTS.md`.

| Option | Default | Meaning |
|--------|---------|---------|
| `directory` | — | Where to create the site. Required. |
| `--force` | off | Scaffold even if the directory is non-empty. |

By default `init` refuses to write into a non-empty directory.

## `new` {#new}

```
ctf new <type> <title> [options]
```

Create a new content file from configuration. `<type>` must be a content type declared in `config.toml`; an unknown one is rejected with a suggestion. The file is written to `content/<type>/<slug>.md` with the required front matter filled in, and the build-ready.

| Option | Default | Meaning |
|--------|---------|---------|
| `type` | — | Content type, e.g. `blog`. Required. |
| `title` | — | Title of the new content. Required. |
| `--slug TEXT` | from title | Explicit slug; also sets the filename. |
| `--description TEXT` | placeholder | Seed the `description` field. |
| `--date DATE` | today | Publication date, `YYYY-MM-DD`. |
| `--draft` / `--no-draft` | `--no-draft` | Mark the file as a draft. |
| `--force` | off | Overwrite an existing file. |
| `--edit` | off | Open the new file in `$EDITOR` afterward. |
| `--root PATH` | `.` | Site root (contains `config.toml`). |

The command is non-interactive: everything is an argument or flag. See [Authoring content](content.md#creating-a-file-with-ctf-new) for what the generated file looks like.

## `build`

```
ctf build [root] [--force] [--drafts]
```

Render the site to `public/`.

| Option | Default | Meaning |
|--------|---------|---------|
| `root` | `.` | Site root (contains `config.toml`). |
| `--force`, `--clean` | off | Ignore the cache and rebuild everything. |
| `--drafts` | off | Include content marked `draft = true`. |

Builds are [incremental](incremental-builds.md) by default: only what changed since the last build is re-rendered. `--force` clears the cache and rebuilds from scratch.

## `check`

```
ctf check [root] [--drafts]
```

Validate the site without writing anything. `check` runs the same pipeline as `build` — it parses `config.toml` and every content file, and renders every template — so any error a real build would raise is caught. But the output goes to a throwaway temporary directory and the incremental cache (`.ctf/`) is left untouched, so nothing in the site is created or changed. It exits non-zero on the first error, which makes it useful in CI or a pre-commit hook.

| Option | Default | Meaning |
|--------|---------|---------|
| `root` | `.` | Site root (contains `config.toml`). |
| `--drafts` | off | Include content marked `draft = true`. |

## `serve`

```
ctf serve [root] [--port PORT] [--drafts/--no-drafts] [--reload/--no-reload]
```

Serve `public/` with file watching and live reload — the dev server.

| Option | Default | Meaning |
|--------|---------|---------|
| `root` | `.` | Site root. |
| `--port`, `-p` | `8000` | Port to serve on. |
| `--drafts` / `--no-drafts` | `--drafts` | Include drafts. **On by default here**, unlike `build`. |
| `--reload` / `--no-reload` | `--reload` | Watch files and live-reload the browser. |

`serve` previews the site at the local root regardless of `base_url`, so hosting paths don't get in the way while you work. On each change it runs an incremental rebuild and refreshes connected browsers.

## Error output

When something you can fix goes wrong — a bad config key, an unparseable content file, a missing front-matter field — `ctf` prints a flat `error:` message naming what failed and why, then exits non-zero. It won't dump a Python traceback for these; a traceback means you've hit an actual bug.
