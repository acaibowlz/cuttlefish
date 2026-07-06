+++
title = "Front Matter"
slug = "front-matter"
date = 2026-06-15
description = "A tour of the TOML front matter that tops every content file."
tags = ["meta"]
featured = true
+++

Every content file opens with **front matter**: a small block of TOML
between `+++` fences that sets the page's metadata. Everything after the
closing fence is the Markdown body you're reading now.

```toml
+++
title = "My Post"
date = 2026-06-21
description = "One line that shows up in listings."
+++
```

## Required fields

Blog posts — and every content type except `pages` — need three fields:

- `title` — the page's heading and its `<title>`.
- `description` — a one-line summary shown in listings.
- `date` — the publication date.

Leave one out and the build stops and names the file, so a typo never ships
silently.

## Dates

`date` is a plain `YYYY-MM-DD` value written **without quotes**:

```toml
date = 2026-06-21      # a real date
date = "2026-06-21"    # rejected — this is a string
```

A time component like `2026-06-21T09:30:00Z` is rejected too: the value has
to be a calendar day and nothing more.

## Optional fields

Everything else is optional:

```toml
slug = "custom-url"        # override the URL (defaults to the filename)
tags = ["python", "ssg"]   # any taxonomy configured in config.toml
featured = true            # also list it in the home page's featured section
draft = true               # hide from `ctf build`; still shown by `ctf serve`
```

This post, for example, sets `slug = "front-matter"` (so it lives at
`/blog/front-matter/` rather than `/blog/second-post/`), a single `tag`, and
`featured = true`. Mix and match freely — the three required fields are the
only hard rule.
