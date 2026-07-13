+++
name = "reading-time"
description = "Show estimated reading time on single article pages."
+++

**What** — adds an "N min read" estimate to single-content pages, computed from the
body word count at build time (no JavaScript).

**Where** — the single-content templates (`blog.html`, …) and `main.css`. It can't
appear on index or listing pages: those render summaries without the body, so the
word count isn't available there.

**When** — use it on any content type whose template renders the body. Skip it if
you want reading time *in listings* — that's a core feature, not a recipe.

**How**

1. In the single-content template, next to the post meta, add:

   ```jinja
   {% set words = page.body_html | striptags | wordcount %}
   {% set minutes = [1, (words / 200) | round(0, 'ceil') | int] | max %}
   <span class="reading-time">{{ minutes }} min read</span>
   ```

   `striptags` drops HTML so tags aren't counted; `200` is words-per-minute, and
   `[1, …] | max` guarantees at least "1 min read".

2. Add a rule to `static/css/main.css`, using tokens rather than literals:

   ```css
   .reading-time { color: var(--muted); font-size: 0.9em; }
   ```

Preview with `ctf serve` and confirm the estimate on a post. It's word-based, so
code and images are under-counted — fine for an estimate.
