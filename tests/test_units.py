"""Unit tests for parsing, permalinks, and config validation."""

from __future__ import annotations

import pytest

from ass.config import ConfigError, parse_config
from ass.content import split_front_matter
from ass.permalink import PermalinkError, resolve_permalink, slugify


def test_split_front_matter_basic():
    meta, body = split_front_matter('+++\ntitle = "Hi"\n+++\n# Body\n')
    assert meta == {"title": "Hi"}
    assert body.strip() == "# Body"


def test_split_front_matter_none():
    meta, body = split_front_matter("# Just markdown\n")
    assert meta == {}
    assert body.startswith("# Just markdown")


def test_split_front_matter_unclosed():
    from ass.content import ContentError

    with pytest.raises(ContentError):
        split_front_matter('+++\ntitle = "Hi"\n# never closed\n')


def test_resolve_permalink_tokens():
    import datetime

    url = resolve_permalink(
        "/blog/{year}/{slug}/", date=datetime.date(2026, 6, 21), slug="hello"
    )
    assert url == "/blog/2026/hello/"


def test_resolve_permalink_unknown_token():
    with pytest.raises(PermalinkError):
        resolve_permalink("/x/{nope}/", slug="a")


def test_slugify():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("  Multiple   Spaces ") == "multiple-spaces"


def test_config_pages_with_index_rejected():
    raw = {
        "content_types": {
            "pages": {
                "template": "page.html",
                "permalink": "/{slug}/",
                "index_template": "x.html",
                "index_permalink": "/pages/",
            }
        }
    }
    with pytest.raises(ConfigError):
        parse_config(raw)


def test_config_missing_required_key():
    raw = {"content_types": {"blog": {"template": "blog.html"}}}  # no permalink
    with pytest.raises(ConfigError):
        parse_config(raw)


def test_config_order_default_and_validation():
    raw = {"content_types": {"blog": {"template": "b.html", "permalink": "/b/{slug}/"}}}
    cfg = parse_config(raw)
    assert cfg.content_types["blog"].order == "desc"
    assert cfg.content_types["blog"].descending is True

    bad = {"content_types": {"blog": {"template": "b.html", "permalink": "/b/{slug}/", "order": "newest"}}}
    with pytest.raises(ConfigError):
        parse_config(bad)


def test_config_paginate_default_and_validation():
    def ct(**extra):
        return {"content_types": {"blog": {"template": "b.html", "permalink": "/b/{slug}/", **extra}}}

    # Omitted disables pagination; a non-negative integer is taken as-is.
    assert parse_config(ct()).content_types["blog"].paginate == 0
    assert parse_config(ct(paginate=10)).content_types["blog"].paginate == 10

    # Everything else is rejected with a clean ConfigError, not a traceback.
    for bad in ("", -5, 1.5, True, "ten"):
        with pytest.raises(ConfigError):
            parse_config(ct(paginate=bad))


def test_config_unknown_keys_rejected():
    ct = {"template": "b.html", "permalink": "/b/{slug}/"}

    # A valid config with only known keys parses.
    parse_config({"title": "X", "content_types": {"blog": dict(ct)}})

    # Unknown keys are rejected in every strict scope (top level + each table).
    bad_configs = [
        {"titel": "X"},                                                  # top level
        {"content_types": {"blog": {**ct, "index_tempalte": "i.html"}}}, # content type
        {"taxonomies": {"tags": {"template": "t.html", "permalink": "/t/{term}/", "paginate": 5}}},
        {"home": {"template": "h.html", "recnt": {}}},                   # home
        {"home": {"template": "h.html", "recent": {"type": "blog", "cnt": 5}}},  # nested recent
        {"nav": {"enabledd": True}},                                     # nav
    ]
    for raw in bad_configs:
        with pytest.raises(ConfigError):
            parse_config(raw)


def test_nav_pairs_labels_and_links():
    cfg = parse_config({
        "nav": {"enabled": True, "labels": ["Blog", "About"], "links": ["/blog/", "/about/"]}
    })
    assert cfg.nav.enabled is True
    assert [(i.label, i.link) for i in cfg.nav.items] == [("Blog", "/blog/"), ("About", "/about/")]


def test_nav_length_mismatch_rejected():
    with pytest.raises(ConfigError):
        parse_config({"nav": {"labels": ["A", "B"], "links": ["/a/"]}})


def test_nav_absent_defaults_disabled():
    cfg = parse_config({})
    assert cfg.nav.enabled is False
    assert cfg.nav.items == ()
