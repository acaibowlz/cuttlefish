"""Unit tests for `config.py`: strict parsing and validation of config.toml."""

from __future__ import annotations

import pytest

from cuttlefish.config import ConfigError, parse_config


def _tax_config(**taxonomy_extra):
    tax = {"template": "t.html", "permalink": "/t/{term}/", **taxonomy_extra}
    return parse_config({"taxonomies": {"tags": tax}})


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
        {"nav": {"enabledd": True}},                                     # nav
    ]
    for raw in bad_configs:
        with pytest.raises(ConfigError):
            parse_config(raw)


def test_taxonomy_multiple_defaults_true():
    assert _tax_config().taxonomies["tags"].multiple is True


def test_taxonomy_multiple_must_be_bool():
    with pytest.raises(ConfigError):
        _tax_config(multiple="yes")


def test_home_recent_multiple_sections():
    cfg = parse_config({
        "content_types": {
            "blog": {"template": "b.html", "permalink": "/b/{slug}/"},
            "project": {"template": "p.html", "permalink": "/p/{slug}/"},
        },
        "home": {"template": "home.html", "recent": {"blog": 5, "project": 3}},
    })
    assert cfg.home.recent == {"blog": 5, "project": 3}


def test_home_recent_validation():
    base = {"content_types": {"blog": {"template": "b.html", "permalink": "/b/{slug}/"}}}

    def home(recent):
        return {**base, "home": {"template": "home.html", "recent": recent}}

    # Unknown content type, bad counts.
    for recent in ({"blgo": 5}, {"blog": -1}, {"blog": "five"}, {"blog": True}):
        with pytest.raises(ConfigError):
            parse_config(home(recent))


def test_home_rejects_removed_featured_key():
    # 'featured' was removed in favor of taxonomy-based curation; a leftover key
    # is an unknown-key error rather than a silently ignored no-op.
    base = {"content_types": {"blog": {"template": "b.html", "permalink": "/b/{slug}/"}}}
    with pytest.raises(ConfigError):
        parse_config({**base, "home": {"template": "home.html", "featured": {"blog": 2}}})


def test_taxonomy_sort_parsed_with_defaults():
    cfg = parse_config({
        "taxonomies": {
            "tags": {"template": "t.html", "permalink": "/t/{term}/"},
            "category": {
                "template": "c.html", "permalink": "/c/{term}/", "multiple": False,
                "sort_by": "count", "order": "desc", "home": True,
            },
        },
    })
    tags = cfg.taxonomies["tags"]
    assert (tags.sort_by, tags.order, tags.home) == ("name", "asc", False)  # defaults
    # Term-page item order defaults to newest-first, like a type index.
    assert (tags.item_sort_by, tags.item_order) == ("date", "desc")
    category = cfg.taxonomies["category"]
    assert (category.sort_by, category.order, category.home) == ("count", "desc", True)


def test_taxonomy_item_sort_parsed_and_validated():
    def tax(items):
        return {"taxonomies": {"tags": {
            "template": "t.html", "permalink": "/t/{term}/", "items": items,
        }}}

    cfg = parse_config(tax({"sort_by": "weight", "order": "asc"}))
    tags = cfg.taxonomies["tags"]
    assert (tags.item_sort_by, tags.item_order) == ("weight", "asc")

    # order is validated (asc/desc); unknown keys in the sub-table are rejected.
    # sort_by stays open-ended, so it is NOT checked against a closed set here.
    for items in ({"order": "up"}, {"limit": 5}):
        with pytest.raises(ConfigError):
            parse_config(tax(items))


def test_taxonomy_sort_validation():
    def tax(opts):
        return {"taxonomies": {"tags": {"template": "t.html", "permalink": "/t/{term}/", **opts}}}

    bad = [
        {"sort_by": "date"},   # bad sort_by
        {"order": "up"},       # bad order
        {"home": "yes"},       # home must be a boolean
        {"limit": 5},          # unknown key
    ]
    for opts in bad:
        with pytest.raises(ConfigError):
            parse_config(tax(opts))


def test_profile_parsed():
    cfg = parse_config({
        "profile": {
            "name": "Jane",
            "bio": "Hi there.",
            "avatar": "/img/a.svg",
            "email": "jane@example.com",
            "socials": {"github": "https://github.com/jane", "mastodon": "https://m/@jane"},
        },
        "home": {"template": "home.html"},
    })
    assert cfg.profile.name == "Jane"
    assert cfg.profile.email == "jane@example.com"
    # socials keep config order (github before mastodon).
    assert list(cfg.profile.socials) == ["github", "mastodon"]


def test_profile_defaults_absent():
    cfg = parse_config({"title": "X"})
    assert cfg.profile is None


def test_profile_validation():
    # Unknown [profile] key and bad socials type are rejected. Author details
    # are site-wide (site.profile), so there is no [home] toggle to validate.
    for raw in (
        {"profile": {"nam": "x"}},
        {"profile": {"socials": "nope"}},
    ):
        with pytest.raises(ConfigError):
            parse_config(raw)


def test_params_free_form():
    # [params] is the escape hatch: arbitrary keys pass through untouched, even
    # ones that would be rejected anywhere else.
    cfg = parse_config({
        "params": {"accent": "teal", "show_sidebar": True, "nested": {"a": 1}},
    })
    assert cfg.params == {"accent": "teal", "show_sidebar": True, "nested": {"a": 1}}
    # Absent table defaults to empty, and a non-table [params] is rejected.
    assert parse_config({"title": "X"}).params == {}
    with pytest.raises(ConfigError):
        parse_config({"params": "nope"})


def test_config_base_path_derived_from_base_url():
    assert parse_config({"base_url": "https://you.github.io/repo"}).base_path == "/repo"
    assert parse_config({"base_url": "https://example.com"}).base_path == ""
    assert parse_config({"base_url": "https://example.com/"}).base_path == ""
    assert parse_config({}).base_path == ""


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
