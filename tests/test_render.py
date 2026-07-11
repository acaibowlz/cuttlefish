"""Unit tests for `render.py`: subpath link rewriting."""

from __future__ import annotations

from cuttlefish.render import _prefix_links


def test_prefix_links():
    html = '<a href="/blog/">x</a> <link href="/css/m.css"> <img src="/i.png">'
    out = _prefix_links(html, "/repo")
    assert 'href="/repo/blog/"' in out
    assert 'href="/repo/css/m.css"' in out
    assert 'src="/repo/i.png"' in out

    # External, protocol-relative, and anchor links are left alone.
    keep = '<a href="https://x.com/">e</a> <a href="//cdn/x">p</a> <a href="#top">a</a>'
    assert _prefix_links(keep, "/repo") == keep
