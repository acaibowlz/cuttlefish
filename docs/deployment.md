# Deployment

`ctf build` renders the whole site to `public/` — plain HTML, your CSS, copied static files, and a `sitemap.xml`. There's no server and no runtime; deploying is just putting that folder online. This page covers the common hosts and the one setting that trips people up: `base_url`.

## The build output

```
ctf build
```

Everything lands in `public/`. Upload its *contents* to any static host and you're live. Nothing in there needs a build step on the host's side — it's already the finished site.

`public/` is regenerated on every build, so there's no reason to commit it; add it to `.gitignore` and let your host build it, or upload it from your machine.

## `base_url` and site paths

`base_url` in `config.toml` does two things at build time:

- It sets the absolute URLs in `sitemap.xml`.
- Its **path component** becomes a prefix on every internal link.

That second part is what matters for hosting. If your site lives at the root of a domain, `base_url` has no path and links stay simple:

```toml
base_url = "https://example.com"     # → links like /blog/post/
```

If your site lives under a subpath — the usual case for a GitHub Pages *project* site — put that subpath in `base_url`, and internal links pick it up automatically:

```toml
base_url = "https://you.github.io/my-site"   # → links like /my-site/blog/post/
```

You don't prefix links yourself; the build does it. (The dev server ignores this and always serves at the local root, so `ctf serve` looks right regardless.)

## GitHub Pages

**User or organization site** (`you.github.io`) — served from the domain root:

```toml
base_url = "https://you.github.io"
```

**Project site** (`you.github.io/my-site`) — served from a subpath, so include it:

```toml
base_url = "https://you.github.io/my-site"
```

Then build and publish the output. A minimal GitHub Actions workflow:

```yaml
name: Deploy
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install cuttlefish-ssg
      - run: ctf build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: public
      - uses: actions/deploy-pages@v4
```

## Netlify / Cloudflare Pages

Both build from your repo. Point them at cuttlefish:

- **Build command:** `pip install cuttlefish-ssg && ctf build`
- **Publish directory:** `public`

Set `base_url` to your final domain. On these hosts the site is served from the root, so `base_url` needs no path component (unless you've deliberately put the site under one).

## Custom domain

Serving from your own domain means the site is at the root, so drop any subpath from `base_url`:

```toml
base_url = "https://mysite.com"
```

If your host uses a `CNAME` file (GitHub Pages does), drop it in `static/` — everything in `static/` is copied verbatim to the site root, so `static/CNAME` becomes `public/CNAME` on every build.

## Sitemap

`ctf build` writes `public/sitemap.xml` from the pages it renders, using `base_url` for the absolute URLs. Keep `base_url` set to your real domain so the sitemap points where the site actually lives, and reference it from a `robots.txt` (drop one in `static/`) if you want search engines to find it.
