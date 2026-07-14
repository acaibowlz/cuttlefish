"""Unit tests for `robots.py`: rendering and the write/override behavior."""

from __future__ import annotations

from pathlib import Path

from cuttlefish.robots import ROBOTS_FILENAME, render_robots, write_robots


def test_render_robots_allows_all_and_points_at_sitemap():
    text = render_robots("https://example.com")
    assert "User-agent: *" in text
    assert "Allow: /" in text
    assert "Sitemap: https://example.com/sitemap.xml" in text


def test_render_robots_strips_trailing_slash_on_base_url():
    # No double slash before the sitemap filename.
    assert "https://example.com/sitemap.xml" in render_robots("https://example.com/")


def test_write_robots_writes_when_base_url_set(tmp_path: Path):
    assert write_robots(tmp_path, "https://example.com", user_provided=False) is True
    assert (tmp_path / ROBOTS_FILENAME).read_text().startswith("User-agent: *")


def test_write_robots_skips_and_prunes_without_base_url(tmp_path: Path):
    stale = tmp_path / ROBOTS_FILENAME
    stale.write_text("old")
    assert write_robots(tmp_path, "", user_provided=False) is False
    # A stale generated file is removed when base_url is cleared.
    assert not stale.exists()


def test_write_robots_stands_aside_for_user_provided(tmp_path: Path):
    # A site-provided robots.txt (already copied from static/) must not be touched.
    provided = tmp_path / ROBOTS_FILENAME
    provided.write_text("User-agent: *\nDisallow: /private/\n")
    assert write_robots(tmp_path, "https://example.com", user_provided=True) is False
    assert provided.read_text() == "User-agent: *\nDisallow: /private/\n"
