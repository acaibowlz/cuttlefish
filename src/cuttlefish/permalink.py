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


def slugify(value: str) -> str:
    """Turn a filename stem or title into a URL-safe slug."""
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "untitled"
