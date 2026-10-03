"""Generate the site's RSS 2.0 feed from the content types that opt in.

One feed per site, at :data:`FEED_PATH`: it merges the most recent items of
every type with ``feed = true``, newest first. Its links are **absolute**, so —
like ``sitemap.xml`` — it is only produced when ``base_url`` is set. It is a *summary*
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
from cuttlefish.permalink import encode_url

#: Site path of the feed. Fixed rather than derived from a type's index, so
#: renaming or re-permalinking a type never moves subscribers' URL.
FEED_PATH = "/feed.xml"

#: Cap on entries per feed, newest first. A feed advertises "what's new", not the
#: whole archive, so a fixed cap keeps it small without adding another config knob.
FEED_MAX_ITEMS = 20


def _rfc822(value: date) -> str:
    """Format a plain date as an RFC-822 datetime at midnight UTC (RSS ``pubDate``)."""
    return format_datetime(datetime(value.year, value.month, value.day, tzinfo=UTC))


def render_rss(
    items: list[ContentItem],
    *,
    site_title: str,
    base_url: str,
    site_description: str = "",
    lang: str = "",
) -> str:
    """Render an RSS 2.0 document for *items* (already ordered newest-first).

    The channel links to the site root and advertises :data:`FEED_PATH` as its
    own address, both made absolute with *base_url*.
    """
    channel_link = base_url + "/"
    self_link = base_url + FEED_PATH
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        "  <channel>",
        f"    <title>{escape(site_title)}</title>",
        f"    <link>{escape(channel_link)}</link>",
        # RSS requires a channel description; the title stands in when unset.
        f"    <description>{escape(site_description or site_title)}</description>",
        f'    <atom:link href="{escape(self_link)}" rel="self" type="application/rss+xml"/>',
    ]
    if lang:
        lines.append(f"    <language>{escape(lang)}</language>")
    # lastBuildDate reflects the newest item, so it is derived from content (stable
    # across rebuilds) rather than the wall clock (which would churn the file).
    newest = max((i.date for i in items if i.date is not None), default=None)
    if newest is not None:
        lines.append(f"    <lastBuildDate>{_rfc822(newest)}</lastBuildDate>")
    for item in items:
        link = base_url + encode_url(item.url)
        lines.append("    <item>")
        lines.append(f"      <title>{escape(item.title)}</title>")
        lines.append(f"      <link>{escape(link)}</link>")
        lines.append(f'      <guid isPermaLink="true">{escape(link)}</guid>')
        if item.date is not None:
            lines.append(f"      <pubDate>{_rfc822(item.date)}</pubDate>")
        if item.description:
            lines.append(f"      <description>{escape(item.description)}</description>")
        # The feed mixes types; the category lets readers label or filter them.
        lines.append(f"      <category>{escape(item.type)}</category>")
        lines.append("    </item>")
    lines.append("  </channel>")
    lines.append("</rss>")
    return "\n".join(lines) + "\n"


def write_feed(
    public_dir: Path,
    items: list[ContentItem],
    *,
    site_title: str,
    base_url: str,
    site_description: str = "",
    lang: str = "",
) -> str:
    """Render and write the feed to ``public/feed.xml``; return its output path.

    The feed's links are absolute (built from *base_url*), so it is written
    directly here rather than through the renderer's base-path link rewriting,
    which only touches root-relative URLs.
    """
    xml = render_rss(
        items,
        site_title=site_title,
        base_url=base_url,
        site_description=site_description,
        lang=lang,
    )
    output_rel = FEED_PATH.lstrip("/")
    dest = public_dir / output_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(xml, encoding="utf-8")
    return output_rel
