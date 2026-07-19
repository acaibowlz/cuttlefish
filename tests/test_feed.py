"""Unit + integration tests for RSS feeds (`feed.py` and its build wiring)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from cuttlefish.content import ContentItem
from cuttlefish.feed import feed_url_path, render_rss
from tests.conftest import append, read

# -- unit: rendering -------------------------------------------------------


def _item(title: str, url: str, description: str, d: date | None) -> ContentItem:
    return ContentItem(
        type="blog",
        slug=url.strip("/").split("/")[-1],
        title=title,
        description=description,
        date=d,
        draft=False,
        cover="",
        body_html="<p>body</p>",
        taxonomies={},
        params={},
        source_rel=f"content/blog/{url.strip('/')}.md",
        url=url,
        output_rel=url.strip("/") + "/index.html",
    )


def test_feed_url_path_appends_feed_xml():
    assert feed_url_path("/blog/") == "/blog/feed.xml"


def test_render_rss_structure_and_absolute_links():
    items = [
        _item("Newest", "/blog/newest/", "The newest post.", date(2026, 6, 15)),
        _item("Older", "/blog/older/", "An older post.", date(2026, 6, 1)),
    ]
    xml = render_rss(
        items,
        site_title="Demo Site",
        base_url="https://example.com",
        channel_path="/blog/",
        self_path="/blog/feed.xml",
    )
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert '<rss version="2.0"' in xml
    assert "<title>Demo Site</title>" in xml
    assert "<link>https://example.com/blog/</link>" in xml
    # atom:self link advertises the feed's own address.
    assert 'href="https://example.com/blog/feed.xml" rel="self"' in xml
    # Item links and guids are absolute.
    assert "<link>https://example.com/blog/newest/</link>" in xml
    assert '<guid isPermaLink="true">https://example.com/blog/newest/</guid>' in xml
    # RFC-822 pubDate, and lastBuildDate reflects the newest item.
    assert "<pubDate>Mon, 15 Jun 2026 00:00:00 +0000</pubDate>" in xml
    assert "<lastBuildDate>Mon, 15 Jun 2026 00:00:00 +0000</lastBuildDate>" in xml
    # Summary feed: descriptions are present, the body never is.
    assert "<description>The newest post.</description>" in xml
    assert "body" not in xml


def test_render_rss_escapes_and_orders_items():
    xml = render_rss(
        [_item("A & B", "/blog/a/", "x < y", date(2026, 1, 1))],
        site_title="S",
        base_url="https://x.com",
        channel_path="/blog/",
        self_path="/blog/feed.xml",
    )
    assert "<title>A &amp; B</title>" in xml
    assert "<description>x &lt; y</description>" in xml


def test_render_rss_omits_pubdate_when_undated():
    xml = render_rss(
        [_item("No date", "/blog/n/", "", None)],
        site_title="S",
        base_url="https://x.com",
        channel_path="/blog/",
        self_path="/blog/feed.xml",
    )
    assert "<pubDate>" not in xml
    assert "<lastBuildDate>" not in xml
    # An empty item description is omitted; only the channel description remains.
    assert xml.count("<description>") == 1


# -- integration: the scaffold build --------------------------------------


def test_scaffold_emits_blog_feed(site: Path, build):
    build(site)
    feed = read(site, "blog/feed.xml")
    assert '<rss version="2.0"' in feed
    assert "<link>https://example.com/blog/hello-world/</link>" in feed
    # Autodiscovery link is present on rendered pages.
    assert 'type="application/rss+xml"' in read(site, "index.html")


def test_feed_is_excluded_from_sitemap(site: Path, build):
    build(site)
    assert "feed.xml" not in read(site, "sitemap.xml")


def test_no_feed_without_base_url(site: Path, build):
    # Clear base_url: the feed (absolute links) is not produced, and no
    # autodiscovery link is emitted.
    cfg = site / "config.toml"
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace(
            'base_url = "https://example.com"', 'base_url = ""'
        ),
        encoding="utf-8",
    )
    build(site)
    assert not (site / "public/blog/feed.xml").exists()
    assert 'type="application/rss+xml"' not in read(site, "index.html")


def test_body_edit_skips_feed_but_meta_edit_rebuilds_it(site: Path, build):
    build(site)
    # A body-only edit leaves every summary unchanged, so the feed is skipped.
    append(site / "content/blog/hello-world.md", "\nAnother paragraph.\n")
    stats = build(site)
    assert stats.feeds == 0
    assert stats.feeds_skipped == 1

    # Editing a summary field (description) rebuilds the feed.
    path = site / "content/blog/hello-world.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "A starter post", "A freshly retitled starter post"
        ),
        encoding="utf-8",
    )
    stats = build(site)
    assert stats.feeds == 1
    assert "freshly retitled" in read(site, "blog/feed.xml")


def test_feed_pruned_when_disabled(site: Path, build):
    build(site)
    assert (site / "public/blog/feed.xml").exists()
    # Turn the feed off; the incremental build prunes the stale file.
    cfg = site / "config.toml"
    cfg.write_text(
        cfg.read_text(encoding="utf-8").replace("feed = true", "feed = false"),
        encoding="utf-8",
    )
    build(site)
    assert not (site / "public/blog/feed.xml").exists()
