"""Unit tests for `sitemap.py`: output-path to URL mapping and rendering."""

from __future__ import annotations

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
