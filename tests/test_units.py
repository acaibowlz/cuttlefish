"""Unit tests for parsing, permalinks, and config validation."""

from __future__ import annotations

import pytest

from cuttlefish.config import PAGES_TYPE, ConfigError, parse_config
from cuttlefish.content import (
    ContentError,
    _extract_taxonomies,
    _require_front_matter,
    render_markdown,
    split_front_matter,
)
from cuttlefish.permalink import PermalinkError, resolve_permalink, slugify
from cuttlefish.render import _prefix_links
from cuttlefish.sitemap import _output_to_url, render_sitemap


def test_split_front_matter_basic():
    meta, body = split_front_matter('+++\ntitle = "Hi"\n+++\n# Body\n')
    assert meta == {"title": "Hi"}
    assert body.strip() == "# Body"


def test_split_front_matter_none():
    meta, body = split_front_matter("# Just markdown\n")
    assert meta == {}
    assert body.startswith("# Just markdown")


def test_split_front_matter_unclosed():
    from cuttlefish.content import ContentError

    with pytest.raises(ContentError):
        split_front_matter('+++\ntitle = "Hi"\n# never closed\n')


def test_required_front_matter_ok():
    import datetime

    meta = {"title": "T", "description": "D", "date": datetime.date(2026, 7, 2)}
    _require_front_matter(meta, "blog", "err")  # must not raise


def test_required_front_matter_missing_fields():
    import datetime

    good_date = datetime.date(2026, 7, 2)
    bad = [
        {"description": "D", "date": good_date},   # no title
        {"title": "T", "date": good_date},         # no description
        {"title": "T", "description": "D"},        # no date
        {"title": " ", "description": "D", "date": good_date},  # blank title
    ]
    for meta in bad:
        with pytest.raises(ContentError):
            _require_front_matter(meta, "blog", "err")


def test_required_front_matter_date_must_be_plain_date():
    import datetime

    base = {"title": "T", "description": "D"}
    # A quoted date is a string, not a TOML date — rejected (not silently ignored).
    # A date-time carries a time component — also rejected; must be plain YYYY-MM-DD.
    for bad_date in ("2026-07-02", datetime.datetime(2026, 7, 2, 9, 30)):
        with pytest.raises(ContentError):
            _require_front_matter({**base, "date": bad_date}, "blog", "err")


def test_required_front_matter_pages_exempt():
    # The standalone pages type needs none of title/description/date.
    _require_front_matter({}, PAGES_TYPE, "err")  # must not raise


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
        {"nav": {"enabledd": True}},                                     # nav
    ]
    for raw in bad_configs:
        with pytest.raises(ConfigError):
            parse_config(raw)


def _tax_config(**taxonomy_extra):
    tax = {"template": "t.html", "permalink": "/t/{term}/", **taxonomy_extra}
    return parse_config({"taxonomies": {"tags": tax}})


def test_taxonomy_multiple_defaults_true():
    assert _tax_config().taxonomies["tags"].multiple is True


def test_taxonomy_multiple_must_be_bool():
    with pytest.raises(ConfigError):
        _tax_config(multiple="yes")


def test_extract_taxonomies_multiple_requires_list():
    config = _tax_config(multiple=True)
    assert _extract_taxonomies({"tags": ["travel", "japan"]}, config) == {
        "tags": ["travel", "japan"]
    }
    # A bare string is rejected when the taxonomy expects multiple terms.
    with pytest.raises(ContentError):
        _extract_taxonomies({"tags": "travel"}, config)


def test_extract_taxonomies_single_requires_string():
    config = _tax_config(multiple=False)
    assert _extract_taxonomies({"tags": "AI"}, config) == {"tags": ["AI"]}
    # A list is rejected when the taxonomy expects a single term.
    with pytest.raises(ContentError):
        _extract_taxonomies({"tags": ["AI", "ML"]}, config)


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


def test_home_featured_parsed_and_validated():
    base = {"content_types": {"blog": {"template": "b.html", "permalink": "/b/{slug}/"}}}
    cfg = parse_config({**base, "home": {"template": "home.html", "featured": {"blog": 2}}})
    assert cfg.home.featured == {"blog": 2}

    # Same rules as recent: unknown type and bad counts are rejected.
    for featured in ({"blgo": 2}, {"blog": -1}, {"blog": True}):
        with pytest.raises(ConfigError):
            parse_config({**base, "home": {"template": "home.html", "featured": featured}})


def test_render_markdown_builds_toc_with_anchors():
    html, toc = render_markdown(
        "## Getting Started\n\ntext\n\n### Install *now*\n\nmore\n"
    )
    # Each heading gets a slug id in the HTML, matching its TOC entry.
    assert '<h2 id="getting-started">' in html
    assert '<h3 id="install-now">' in html
    assert [(e.level, e.id, e.text, e.url) for e in toc] == [
        (2, "getting-started", "Getting Started", "#getting-started"),
        (3, "install-now", "Install now", "#install-now"),
    ]


def test_render_markdown_dedupes_repeated_headings():
    html, toc = render_markdown("# Notes\n\n# Notes\n")
    assert [e.id for e in toc] == ["notes", "notes-1"]
    assert '<h1 id="notes">' in html and '<h1 id="notes-1">' in html


def test_render_markdown_no_headings_gives_empty_toc():
    html, toc = render_markdown("just a paragraph\n")
    assert toc == []
    assert "<p>just a paragraph</p>" in html


def test_content_item_featured_flag():
    from cuttlefish.content import ContentItem

    def make(meta):
        return ContentItem(
            type="blog", slug="s", meta=meta, body_html="", taxonomies={},
            source_rel="content/blog/s.md", url="/b/s/", output_rel="b/s/index.html",
        )

    assert make({"featured": True}).featured is True
    assert make({}).featured is False


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
    category = cfg.taxonomies["category"]
    assert (category.sort_by, category.order, category.home) == ("count", "desc", True)


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


def test_taxonomy_term_ordering():
    from cuttlefish.taxonomy import Term, TaxonomyData, home_taxonomy_terms

    def ordered(sort_by, order):
        cfg = parse_config({"taxonomies": {"tags": {
            "template": "t.html", "permalink": "/t/{term}/",
            "sort_by": sort_by, "order": order,
        }}})
        data = TaxonomyData(taxonomy=cfg.taxonomies["tags"])
        for name, n in [("python", 3), ("meta", 3), ("ssg", 7)]:
            term = Term(taxonomy="tags", name=name, url=f"/t/{name}/", output_rel=f"t/{name}/index.html")
            term.items = list(range(n))
            data.terms[name] = term
        # sorted_terms (index page) and home_taxonomy_terms (home list) agree.
        assert [t.name for t in data.sorted_terms] == [t.name for t in home_taxonomy_terms(data)]
        return [t.name for t in data.sorted_terms]

    # count/desc: most-used first, alphabetical tiebreak for the two 3s.
    assert ordered("count", "desc") == ["ssg", "meta", "python"]
    assert ordered("name", "asc") == ["meta", "python", "ssg"]
    assert ordered("name", "desc") == ["ssg", "python", "meta"]


def test_profile_parsed():
    cfg = parse_config({
        "profile": {
            "name": "Jane",
            "bio": "Hi there.",
            "avatar": "/img/a.svg",
            "email": "jane@example.com",
            "socials": {"github": "https://github.com/jane", "mastodon": "https://m/@jane"},
        },
        "home": {"template": "home.html", "profile": True},
    })
    assert cfg.profile.name == "Jane"
    assert cfg.profile.email == "jane@example.com"
    # socials keep config order (github before mastodon).
    assert list(cfg.profile.socials) == ["github", "mastodon"]
    assert cfg.home.profile is True


def test_profile_defaults_absent():
    cfg = parse_config({"title": "X"})
    assert cfg.profile is None


def test_profile_validation():
    # home.profile true with no [profile] section is an error.
    with pytest.raises(ConfigError):
        parse_config({"home": {"template": "h.html", "profile": True}})
    # Unknown key, non-bool home.profile, and bad socials type are rejected.
    for raw in (
        {"profile": {"nam": "x"}},
        {"profile": {"name": "x"}, "home": {"template": "h.html", "profile": "yes"}},
        {"profile": {"socials": "nope"}},
    ):
        with pytest.raises(ConfigError):
            parse_config(raw)


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


def test_config_base_path_derived_from_base_url():
    assert parse_config({"base_url": "https://you.github.io/repo"}).base_path == "/repo"
    assert parse_config({"base_url": "https://example.com"}).base_path == ""
    assert parse_config({"base_url": "https://example.com/"}).base_path == ""
    assert parse_config({}).base_path == ""


def test_prefix_links():
    html = '<a href="/blog/">x</a> <link href="/css/m.css"> <img src="/i.png">'
    out = _prefix_links(html, "/repo")
    assert 'href="/repo/blog/"' in out
    assert 'href="/repo/css/m.css"' in out
    assert 'src="/repo/i.png"' in out

    # External, protocol-relative, and anchor links are left alone.
    keep = '<a href="https://x.com/">e</a> <a href="//cdn/x">p</a> <a href="#top">a</a>'
    assert _prefix_links(keep, "/repo") == keep


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
