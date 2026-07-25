"""Resolve permalink patterns into URLs and output filesystem paths.

A permalink pattern is a string like ``/blog/{slug}/`` containing tokens. We
substitute tokens, normalise the URL, and map it to a "pretty URL" output file
(``/blog/post/`` -> ``public/blog/post/index.html``).

Supported tokens: ``{slug}``, ``{type}``, ``{year}``, ``{month}``, ``{day}``,
``{term}``, ``{taxonomy}``.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

from cuttlefish.errors import CuttlefishError

_TOKEN_RE = re.compile(r"\{(\w+)\}")


class PermalinkError(CuttlefishError):
    """Raised when a permalink pattern references an unknown/missing token."""

    default_summary = "Failed to resolve permalink"


def _date_tokens(value: object) -> dict[str, str]:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return {
            "year": f"{value.year:04d}",
            "month": f"{value.month:02d}",
            "day": f"{value.day:02d}",
        }
    return {}


def resolve_permalink(pattern: str, *, date: object = None, **tokens: str) -> str:
    """Substitute tokens in *pattern* and return a normalised URL.

    Date-derived tokens (``year``/``month``/``day``) are filled from *date*.
    The result always starts with ``/`` and, unless it points at a file with an
    extension, ends with ``/``.
    """
    values: dict[str, str] = {k: str(v) for k, v in tokens.items() if v is not None}
    values.update(_date_tokens(date))

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise PermalinkError(
                f"Permalink '{pattern}' uses unknown token '{{{name}}}'. "
                f"Available: {sorted(values)}."
            )
        return values[name]

    url = _TOKEN_RE.sub(replace, pattern)
    if not url.startswith("/"):
        url = "/" + url
    # Collapse duplicate slashes (e.g. from an empty token).
    url = re.sub(r"/{2,}", "/", url)
    # Pretty URLs end in a slash unless they target an explicit file.
    last = url.rsplit("/", 1)[-1]
    if "." not in last and not url.endswith("/"):
        url += "/"
    return url


def output_path(url: str, public_dir: Path) -> Path:
    """Map a site URL to the file it is written to under *public_dir*.

    ``/blog/post/`` -> ``public/blog/post/index.html``;
    ``/feed.xml`` -> ``public/feed.xml``.
    """
    rel = url.lstrip("/")
    if rel == "" or url.endswith("/"):
        return public_dir / rel / "index.html"
    return public_dir / rel


def encode_url(url: str) -> str:
    """Percent-encode a site path for embedding in a machine-read document.

    Slugs keep their non-ASCII letters (``/blog/新貼文/``) so filenames and the
    address bar stay readable — browsers percent-encode on the wire themselves,
    so HTML ``href``s need no help. But sitemap ``<loc>`` and RSS ``<link>`` are
    parsed as strict URIs, which are ASCII-only, so those two boundaries encode.
    Only the site path is encoded, never ``base_url`` — its ``//`` and ``:`` are
    structure, not data. ``safe`` keeps every RFC 3986 reserved delimiter, so a
    URL that already contains ``?``/``&``/``#`` keeps its structure and only the
    non-ASCII (and spaces) get encoded.
    """
    return quote(url, safe="/:@!$&'()*+,;=?#~")


def slugify(value: str) -> str:
    """Turn a filename stem or title into a URL-safe slug.

    Non-ASCII **letters** are deliberately kept: ``\\w`` is Unicode-aware, so
    ``新貼文`` and ``café`` survive while every filesystem- and URL-hostile
    character (``<>:/|?*#\\``, quotes, brackets) is stripped. Transliterating
    instead would need a dependency and mangles CJK; collapsing to ASCII would
    silently collide every non-Latin title into one slug.
    """
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "untitled"
