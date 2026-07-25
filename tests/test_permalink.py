"""Unit tests for `permalink.py`: token substitution and slugify."""

from __future__ import annotations

import datetime

import pytest

from cuttlefish.permalink import PermalinkError, encode_url, resolve_permalink, slugify


def test_resolve_permalink_tokens():
    url = resolve_permalink("/blog/{year}/{slug}/", date=datetime.date(2026, 6, 21), slug="hello")
    assert url == "/blog/2026/hello/"


def test_resolve_permalink_unknown_token():
    with pytest.raises(PermalinkError):
        resolve_permalink("/x/{nope}/", slug="a")


def test_slugify():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("  Multiple   Spaces ") == "multiple-spaces"


def test_slugify_preserves_non_ascii_letters():
    # Unicode letters survive (no transliteration, no collapse to a shared
    # fallback); only URL/filesystem-hostile characters are stripped.
    assert slugify("新貼文") == "新貼文"
    assert slugify("日本語 の 記事") == "日本語-の-記事"
    assert slugify("Café Crème") == "café-crème"
    assert slugify("中文，標點。") == "中文標點"
    assert slugify("a/b:c?d*e|f") == "abcdef"
    # Two different non-Latin titles must not collide on one slug.
    assert slugify("技術") != slugify("設計")


def test_encode_url_percent_encodes_non_ascii_only():
    assert encode_url("/blog/新貼文/") == "/blog/%E6%96%B0%E8%B2%BC%E6%96%87/"
    assert encode_url("/blog/hello-world/") == "/blog/hello-world/"
    # Reserved delimiters are structure and stay literal.
    assert encode_url("/?a=1&b=2#top") == "/?a=1&b=2#top"
