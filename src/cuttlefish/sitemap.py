"""Generate ``sitemap.xml`` from the pages a build produces.

A sitemap lists the site's public URLs as **absolute** links, so it needs
``base_url`` from the config. The URL set comes straight from the build's HTML
page outputs (content pages + aggregates), so it always matches what was
actually published. Static assets are excluded — a sitemap lists pages, not
files.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from cuttlefish.permalink import encode_url

SITEMAP_FILENAME = "sitemap.xml"

_INDEX_FILE = "index.html"


def _output_to_url(output_rel: str) -> str:
    """Map an output path (``blog/post/index.html``) to a site URL (``/blog/post/``)."""
    out = output_rel.lstrip("/")
    if out == _INDEX_FILE or out.endswith("/" + _INDEX_FILE):
        out = out[: -len(_INDEX_FILE)]
    return "/" + out


def render_sitemap(
    urls: Iterable[str], base_url: str, lastmod: Mapping[str, date] | None = None
) -> str:
    """Render a sitemap XML document for *urls* (site-root paths) under *base_url*.

    *lastmod* maps a URL to its ``<lastmod>`` date; URLs without one omit it.
    """
    lastmod = lastmod or {}
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for url in urls:
        loc = f"<loc>{escape(base_url + encode_url(url))}</loc>"
        mod = f"<lastmod>{lastmod[url].isoformat()}</lastmod>" if url in lastmod else ""
        lines.append(f"  <url>{loc}{mod}</url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def write_sitemap(
    public_dir: Path,
    page_outputs: Iterable[str],
    base_url: str,
    lastmod: Mapping[str, date] | None = None,
) -> bool:
    """Write ``public/sitemap.xml`` from *page_outputs*; return whether it was written.

    *lastmod* maps an output path to its last-modified date (content pages only;
    aggregates have no single date and omit ``<lastmod>``).

    Skips (and removes any stale file) when *base_url* is empty, since a sitemap
    must contain absolute URLs.
    """
    target = public_dir / SITEMAP_FILENAME
    if not base_url:
        target.unlink(missing_ok=True)
        return False
    urls = sorted({_output_to_url(o) for o in page_outputs})
    by_url = {_output_to_url(o): d for o, d in (lastmod or {}).items()}
    target.write_text(render_sitemap(urls, base_url, by_url), encoding="utf-8")
    return True
