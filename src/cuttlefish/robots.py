"""Generate ``robots.txt`` and point crawlers at the sitemap.

The generated file permits all crawlers and advertises the sitemap's **absolute**
URL, so it only makes sense once ``base_url`` is set — the same condition under
which ``sitemap.xml`` is emitted. A site that ships its own ``static/robots.txt``
keeps full control: that file is copied verbatim to the site root, and this
generator stands aside rather than clobber it.
"""

from __future__ import annotations

from pathlib import Path

from cuttlefish.sitemap import SITEMAP_FILENAME

ROBOTS_FILENAME = "robots.txt"


def render_robots(base_url: str) -> str:
    """Render a permissive ``robots.txt`` that advertises the sitemap."""
    sitemap_url = f"{base_url.rstrip('/')}/{SITEMAP_FILENAME}"
    return f"User-agent: *\nAllow: /\n\nSitemap: {sitemap_url}\n"


def write_robots(public_dir: Path, base_url: str, *, user_provided: bool) -> bool:
    """Write ``public/robots.txt``; return whether *this generator* wrote it.

    Stands aside when the site ships its own ``static/robots.txt``
    (*user_provided*) — the verbatim static copy wins. Otherwise writes a
    generated file when *base_url* is set (it advertises the sitemap, which needs
    an absolute URL) and removes any stale generated file when it is not.
    """
    if user_provided:
        return False
    target = public_dir / ROBOTS_FILENAME
    if not base_url:
        target.unlink(missing_ok=True)
        return False
    target.write_text(render_robots(base_url), encoding="utf-8")
    return True
