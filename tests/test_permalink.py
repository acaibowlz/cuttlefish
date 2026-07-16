"""Unit tests for `permalink.py`: token substitution and slugify."""

from __future__ import annotations

import datetime

import pytest

from cuttlefish.permalink import PermalinkError, resolve_permalink, slugify


def test_resolve_permalink_tokens():
    url = resolve_permalink("/blog/{year}/{slug}/", date=datetime.date(2026, 6, 21), slug="hello")
    assert url == "/blog/2026/hello/"


def test_resolve_permalink_unknown_token():
    with pytest.raises(PermalinkError):
        resolve_permalink("/x/{nope}/", slug="a")


def test_slugify():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("  Multiple   Spaces ") == "multiple-spaces"
