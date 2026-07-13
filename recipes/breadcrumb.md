+++
name = "breadcrumb"
description = "Add a breadcrumb trail (Home / Section / Page) to content pages."
+++

**What** — adds a breadcrumb nav (Home / Section / Page title) to the top of
single-content pages. Pure markup; no JavaScript.

**Where** — the single-content templates (`blog.html`, …) and `main.css`. The
middle "Section" crumb links to the content type's index; for the `pages` type
(no index) it's skipped automatically, giving Home / Title.

**When** — any content type. To avoid repeating the block across templates, put it
in a shared partial and `{% include %}` it, or in a `{% block breadcrumb %}` in
`base.html` that content templates fill.

**How**

1. In the single-content template, above the article, add:

   ```jinja
   <nav class="breadcrumb" aria-label="Breadcrumb">
     <ol>
       <li><a href="/">Home</a></li>
       {% set index_url = site.config.content_types[type].get('index_permalink') %}
       {% if index_url %}
       <li><a href="{{ index_url }}">{{ type | capitalize }}</a></li>
       {% endif %}
       <li aria-current="page">{{ page.title }}</li>
     </ol>
   </nav>
   ```

   Write hrefs **root-absolute** (`/`, and the raw `index_permalink`); cuttlefish
   rewrites them for subpath hosting at build time. `site.config` is the parsed
   `config.toml`, so the section URL is read straight from it — no hardcoded
   `/blog/`.

2. Add a rule to `static/css/main.css`, using tokens:

   ```css
   .breadcrumb ol { list-style: none; display: flex; flex-wrap: wrap; gap: 0.4rem; padding: 0; margin: 0 0 1rem; font-size: 0.9em; color: var(--muted); }
   .breadcrumb li + li::before { content: "/"; margin-right: 0.4rem; color: var(--border); }
   .breadcrumb a { color: var(--muted); }
   .breadcrumb a:hover { color: var(--accent); }
   ```

Preview with `ctf serve`: a post gives Home / Blog / Title, a standalone page
Home / Title. Check narrow widths — the trail should wrap, not overflow. The
section label uses `type | capitalize` ("blog" → "Blog"); set it by hand if the
type name isn't presentable.
