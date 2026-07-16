"""Unit tests for `content.py`: front matter, Markdown, and `ContentItem`."""

from __future__ import annotations

import datetime

import pytest

from cuttlefish.config import PAGES_TYPE, parse_config
from cuttlefish.content import (
    ContentError,
    ContentItem,
    _extract_taxonomies,
    _require_front_matter,
    parse_item,
    render_markdown,
    split_front_matter,
)


def _tax_config(**taxonomy_extra):
    tax = {"template": "t.html", "permalink": "/t/{term}/", **taxonomy_extra}
    return parse_config({"taxonomies": {"tags": tax}})


def _item(**overrides):
    """A minimally-populated ContentItem for field-level unit tests."""
    fields = dict(
        type="blog",
        slug="s",
        title="T",
        description="D",
        date=None,
        draft=False,
        cover="",
        body_html="",
        taxonomies={},
        params={},
        source_rel="content/blog/s.md",
        url="/b/s/",
        output_rel="b/s/index.html",
    )
    fields.update(overrides)
    return ContentItem(**fields)


def test_split_front_matter_basic():
    meta, body = split_front_matter('+++\ntitle = "Hi"\n+++\n# Body\n')
    assert meta == {"title": "Hi"}
    assert body.strip() == "# Body"


def test_split_front_matter_none():
    meta, body = split_front_matter("# Just markdown\n")
    assert meta == {}
    assert body.startswith("# Just markdown")


def test_split_front_matter_unclosed():
    with pytest.raises(ContentError):
        split_front_matter('+++\ntitle = "Hi"\n# never closed\n')


def test_required_front_matter_ok():
    meta = {"title": "T", "description": "D", "date": datetime.date(2026, 7, 2)}
    _require_front_matter(meta, "blog", _tax_config(), "err")  # must not raise


def test_required_front_matter_missing_fields():
    good_date = datetime.date(2026, 7, 2)
    bad = [
        {"description": "D", "date": good_date},  # no title
        {"title": "T", "date": good_date},  # no description
        {"title": "T", "description": "D"},  # no date
        {"title": " ", "description": "D", "date": good_date},  # blank title
    ]
    for meta in bad:
        with pytest.raises(ContentError):
            _require_front_matter(meta, "blog", _tax_config(), "err")


def test_required_front_matter_date_must_be_plain_date():
    base = {"title": "T", "description": "D"}
    # A quoted date is a string, not a TOML date — rejected (not silently ignored).
    # A date-time carries a time component — also rejected; must be plain YYYY-MM-DD.
    for bad_date in ("2026-07-02", datetime.datetime(2026, 7, 2, 9, 30)):
        with pytest.raises(ContentError):
            _require_front_matter({**base, "date": bad_date}, "blog", _tax_config(), "err")


def test_required_front_matter_pages_need_only_title():
    # A standalone page needs a title but no description or date.
    _require_front_matter({"title": "About"}, PAGES_TYPE, _tax_config(), "err")  # ok
    for bad in ({}, {"title": " "}, {"description": "D"}):  # missing/blank title
        with pytest.raises(ContentError):
            _require_front_matter(bad, PAGES_TYPE, _tax_config(), "err")


def test_required_front_matter_pages_reject_taxonomy_keys():
    # A page is grouped into no taxonomy listing, so a taxonomy key would be a
    # silent no-op (or worse, leak the page into term pages) — reject it.
    with pytest.raises(ContentError):
        _require_front_matter({"title": "About", "tags": ["x"]}, PAGES_TYPE, _tax_config(), "err")


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


def test_render_markdown_builds_toc_with_anchors():
    html, toc = render_markdown("## Getting Started\n\ntext\n\n### Install *now*\n\nmore\n")
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


def test_render_markdown_supports_mark_and_math():
    # `mark` and `math` only emit markup; math rendering is left to a script the
    # site adds, so we assert on the emitted HTML, not any rendered output.
    html, _ = render_markdown("==key== and $a^2$\n\n$$\nx = y\n$$\n")
    assert "<mark>key</mark>" in html
    assert '<span class="math">\\(a^2\\)</span>' in html
    assert '<div class="math">$$\nx = y\n$$</div>' in html


def test_content_item_sort_value_promoted_and_custom():
    item = _item(title="Zed", params={"weight": 5})
    assert item.sort_value("title") == "Zed"  # promoted -> typed attribute
    assert item.sort_value("weight") == 5  # custom -> params
    assert item.sort_value("missing") is None  # absent custom -> None
    assert item.has_sort_field("title") is True  # promoted always present
    assert item.has_sort_field("weight") is True
    assert item.has_sort_field("missing") is False


def test_parse_item_promotes_fields_and_collects_params(tmp_path):
    cfg = parse_config(
        {
            "content_types": {"blog": {"template": "b.html", "permalink": "/blog/{slug}/"}},
            "taxonomies": {"tags": {"template": "t.html", "permalink": "/t/{term}/"}},
        }
    )
    path = tmp_path / "content" / "blog" / "post.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        '+++\ntitle = "T"\ndescription = "D"\ndate = 2026-01-02\n'
        'cover = "/img/t.jpg"\ntags = ["x"]\nhero_layout = "wide"\n+++\nBody\n',
        encoding="utf-8",
    )
    item = parse_item(path, "blog", cfg)

    assert item.title == "T"
    assert item.date == datetime.date(2026, 1, 2)
    assert item.taxonomies == {"tags": ["x"]}
    # cover is a promoted field: typed on the item and its summary, not in params.
    assert item.cover == "/img/t.jpg"
    assert item.summary.cover == "/img/t.jpg"
    # params is the leftover: promoted fields and taxonomy keys are excluded.
    assert item.params == {"hero_layout": "wide"}


def test_cover_is_optional_and_in_fingerprint(tmp_path):
    cfg = parse_config(
        {"content_types": {"blog": {"template": "b.html", "permalink": "/blog/{slug}/"}}}
    )
    path = tmp_path / "content" / "blog" / "post.md"
    path.parent.mkdir(parents=True)
    base = '+++\ntitle = "T"\ndescription = "D"\ndate = 2026-01-02\n'

    path.write_text(base + "+++\nBody\n", encoding="utf-8")
    without = parse_item(path, "blog", cfg)
    assert without.cover == ""  # optional: absent front matter -> empty string

    path.write_text(base + 'cover = "/img/t.jpg"\n+++\nBody\n', encoding="utf-8")
    with_cover = parse_item(path, "blog", cfg)
    # A listing renders the cover, so it must move the fingerprint when it changes.
    assert with_cover.meta_fingerprint != without.meta_fingerprint
