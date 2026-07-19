"""Generate an RSS 2.0 feed for a content type from its items.

A feed lists a content type's most recent items as **absolute** links, so — like
``sitemap.xml`` — it is only produced when ``base_url`` is set. It is a *summary*
feed: each entry carries the item's title, link, date and description, never the
body. That is deliberate: the feed is fingerprinted over item metadata (see
``graph.build_feed_specs``) and so stays inside the incremental-build model,
exactly like the HTML listings — a body-only edit cannot change it.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

from cuttlefish.content import ContentItem

FEED_FILENAME = "feed.xml"

#: Cap on entries per feed, newest first. A feed advertises "what's new", not the
#: whole archive, so a fixed cap keeps it small without adding another config knob.
FEED_MAX_ITEMS = 20


def feed_url_path(index_permalink: str) -> str:
    """Site path of the feed for a type whose index lives at *index_permalink*.

    ``/blog/`` -> ``/blog/feed.xml``. The index permalink always ends in a slash.
    """
    return index_permalink + FEED_FILENAME


def _rfc822(value: date) -> str:
    """Format a plain date as an RFC-822 datetime at midnight UTC (RSS ``pubDate``)."""
    return format_datetime(datetime(value.year, value.month, value.day, tzinfo=UTC))


def render_rss(
    items: list[ContentItem],
    *,
    site_title: str,
    base_url: str,
    channel_path: str,
    self_path: str,
) -> str:
    """Render an RSS 2.0 document for *items* (already ordered newest-first).

    *channel_path* is the site path of the page the feed represents (the type
    index, e.g. ``/blog/``); *self_path* is the feed's own path
    (``/blog/feed.xml``). Both are made absolute with *base_url*.
    """
    channel_link = base_url + channel_path
    self_link = base_url + self_path
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{escape(site_title)}</title>",
        f"    <link>{escape(channel_link)}</link>",
        f"    <description>{escape(site_title)}</description>",
        f'    <atom:link href="{escape(self_link)}" rel="self" type="application/rss+xml"/>',
    ]
    # lastBuildDate reflects the newest item, so it is derived from content (stable
    # across rebuilds) rather than the wall clock (which would churn the file).
    newest = max((i.date for i in items if i.date is not None), default=None)
    if newest is not None:
        lines.append(f"    <lastBuildDate>{_rfc822(newest)}</lastBuildDate>")
    for item in items:
        link = base_url + item.url
        lines.append("    <item>")
        lines.append(f"      <title>{escape(item.title)}</title>")
        lines.append(f"      <link>{escape(link)}</link>")
        lines.append(f'      <guid isPermaLink="true">{escape(link)}</guid>')
        if item.date is not None:
            lines.append(f"      <pubDate>{_rfc822(item.date)}</pubDate>")
        if item.description:
            lines.append(f"      <description>{escape(item.description)}</description>")
        lines.append("    </item>")
    lines.append("  </channel>")
    lines.append("</rss>")
    return "\n".join(lines) + "\n"


def write_feed(
    public_dir: Path,
    output_rel: str,
    items: list[ContentItem],
    *,
    site_title: str,
    base_url: str,
    channel_path: str,
    self_path: str,
) -> str:
    """Render and write a feed to ``public/<output_rel>``; return *output_rel*.

    The feed's links are absolute (built from *base_url*), so it is written
    directly here rather than through the renderer's base-path link rewriting,
    which only touches root-relative URLs.
    """
    xml = render_rss(
        items,
        site_title=site_title,
        base_url=base_url,
        channel_path=channel_path,
        self_path=self_path,
    )
    dest = public_dir / output_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(xml, encoding="utf-8")
    return output_rel
