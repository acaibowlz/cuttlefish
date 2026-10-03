"""Unit tests for `sitemap.py`: output-path to URL mapping and rendering."""

from __future__ import annotations

from datetime import date

from cuttlefish.sitemap import _output_to_url, render_sitemap


def test_sitemap_output_to_url():
    assert _output_to_url("index.html") == "/"
    assert _output_to_url("blog/index.html") == "/blog/"
    assert _output_to_url("blog/hello/index.html") == "/blog/hello/"
    assert _output_to_url("/tags/meta/index.html") == "/tags/meta/"


def test_sitemap_render_is_sorted_and_absolute():
    xml = render_sitemap(["/blog/", "/"], base_url="https://example.com")
    assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
    assert "<loc>https://example.com/</loc>" in xml
    assert "<loc>https://example.com/blog/</loc>" in xml
    # Ampersands in URLs are XML-escaped.
    assert "&amp;" in render_sitemap(["/?a=1&b=2"], base_url="https://x.com")


def test_sitemap_percent_encodes_unicode_slugs():
    # <loc> is parsed as a strict URI, which is ASCII-only.
    xml = render_sitemap(["/blog/新貼文/"], base_url="https://example.com")
    assert "<loc>https://example.com/blog/%E6%96%B0%E8%B2%BC%E6%96%87/</loc>" in xml


def test_render_sitemap_lastmod_only_where_known():
    xml = render_sitemap(
        ["/", "/blog/post/"], base_url="https://x.com", lastmod={"/blog/post/": date(2026, 3, 4)}
    )
    assert "<loc>https://x.com/blog/post/</loc><lastmod>2026-03-04</lastmod>" in xml
    assert "<url><loc>https://x.com/</loc></url>" in xml
