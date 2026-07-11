"""Tests for ``ctf new`` (content creation from config)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from rich.console import Console

from cuttlefish.config import load_config
from cuttlefish.content import parse_item
from cuttlefish.new import NewContentError, create_content

QUIET = Console(quiet=True)


def make(root: Path, type_name: str, title: str, **kwargs) -> Path:
    return create_content(root, type_name, title, console=QUIET, **kwargs)


def test_new_blog_is_buildable(site: Path, build):
    """A generated dated file parses and builds with no edits."""
    path = make(site, "blog", "My First Post")
    assert path == site / "content" / "blog" / "my-first-post.md"

    # Round-trips through the parser the build uses...
    config = load_config(site)
    item = parse_item(path, "blog", config)
    assert item.title == "My First Post"
    assert item.date == date.today()

    # ...and through a full build.
    build(site)
    assert (site / "public" / "blog" / "my-first-post" / "index.html").is_file()


def test_new_blog_skeleton_fields(site: Path):
    text = make(site, "blog", "Hello There").read_text(encoding="utf-8")
    # Date is an unquoted TOML local date (a quoted date is rejected downstream).
    assert f"date = {date.today().isoformat()}" in text
    assert 'title = "Hello There"' in text
    # A non-empty description is seeded: a blank one fails the dated-type build.
    assert 'description = ""' not in text
    assert "description = " in text


def test_new_pages_skeleton(site: Path, build):
    """Pages carry a slug but no date/description, and build cleanly."""
    path = make(site, "pages", "Contact Me")
    text = path.read_text(encoding="utf-8")
    assert 'slug = "contact-me"' in text
    assert "date =" not in text
    assert "description =" not in text

    build(site)
    assert (site / "public" / "contact-me" / "index.html").is_file()


def test_new_taxonomy_placeholders_are_commented(site: Path):
    """Configured taxonomies appear only as inert, commented placeholders.

    An active placeholder term would leak into the taxonomy's term index.
    """
    text = make(site, "blog", "Post").read_text(encoding="utf-8")
    assert '# tags = ["example"]' in text
    # Not active — no bare `tags =` line.
    assert "\ntags = " not in text


def test_new_slug_derived_and_explicit(site: Path):
    assert make(site, "blog", "A Fancy Title!").stem == "a-fancy-title"
    assert make(site, "blog", "Whatever", slug="custom-one").stem == "custom-one"


def test_new_explicit_options(site: Path):
    text = make(
        site,
        "blog",
        "Post",
        description="Hand-written.",
        date="2025-01-02",
        draft=True,
    ).read_text(encoding="utf-8")
    assert 'description = "Hand-written."' in text
    assert "date = 2025-01-02" in text
    assert "draft = true" in text


def test_new_unknown_type_suggests(site: Path):
    with pytest.raises(NewContentError) as exc:
        make(site, "blogg", "X")
    assert "blog" in str(exc.value)


def test_new_bad_date_rejected(site: Path):
    with pytest.raises(NewContentError):
        make(site, "blog", "X", date="not-a-date")


def test_new_collision_refused_then_forced(site: Path):
    first = make(site, "blog", "Dup")
    with pytest.raises(NewContentError):
        make(site, "blog", "Dup")  # same slug -> same path
    # --force overwrites in place.
    make(site, "blog", "Dup", force=True, description="Second take.")
    assert "Second take." in first.read_text(encoding="utf-8")
