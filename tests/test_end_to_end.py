"""End-to-end full-build tests: `build_site` against the scaffolded site."""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from cuttlefish.build import check_site
from cuttlefish.config import ConfigError
from cuttlefish.content import ContentError
from tests.conftest import read


def _quiet_check(root: Path):
    return check_site(root, console=Console(quiet=True))


def _snapshot(public: Path) -> dict[str, bytes]:
    return {str(p.relative_to(public)): p.read_bytes() for p in public.rglob("*") if p.is_file()}


def test_full_build_outputs(site: Path, build):
    stats = build(site)
    public = site / "public"
    for rel in [
        "index.html",
        "blog/index.html",
        "blog/hello-world/index.html",
        "projects/index.html",
        "projects/example-project/index.html",
        "about/index.html",
        "tags/index.html",
        "tags/meta/index.html",
        "css/main.css",
    ]:
        assert (public / rel).is_file(), f"missing {rel}"
    assert stats.mode == "full"
    assert stats.content == 4  # 2 blog + 1 project + 1 page


def test_markdown_code_highlighting(site: Path, build):
    build(site)
    post = read(site, "blog/hello-world/index.html")
    assert 'class="language-python"' in post


def test_sitemap_generated(site: Path, build):
    stats = build(site)
    assert stats.sitemap is True
    sitemap = read(site, "sitemap.xml")
    # Absolute URLs (scaffold base_url) for content, indexes, and term pages.
    for loc in [
        "https://example.com/",
        "https://example.com/blog/hello-world/",
        "https://example.com/tags/meta/",
    ]:
        assert f"<loc>{loc}</loc>" in sitemap


def _set_subpath(site: Path) -> None:
    cfg = site / "config.toml"
    cfg.write_text(cfg.read_text().replace(
        'base_url = "https://example.com"', 'base_url = "https://you.github.io/repo"'))


def test_subpath_base_url_prefixes_links(site: Path, build):
    _set_subpath(site)
    build(site)
    home = read(site, "index.html")
    assert 'href="/repo/css/main.css"' in home   # asset prefixed
    assert 'href="/repo/blog/"' in home          # nav/link prefixed
    # Output file paths on disk are NOT prefixed.
    assert (site / "public" / "blog" / "hello-world" / "index.html").is_file()
    assert not (site / "public" / "repo").exists()
    # Sitemap uses the full base_url (incl. subpath) with no double prefix.
    assert "<loc>https://you.github.io/repo/blog/</loc>" in read(site, "sitemap.xml")


def test_base_path_override_disables_prefix(site: Path, build):
    """How the dev server builds: preview at the local root, no prefix."""
    _set_subpath(site)
    build(site, base_path="")
    home = read(site, "index.html")
    assert 'href="/css/main.css"' in home
    assert "/repo" not in home


def test_base_path_change_invalidates_cache(site: Path, build):
    """Switching prefix (e.g. build vs serve) must not reuse stale prefixed output."""
    _set_subpath(site)
    build(site)                                  # full, prefix /repo
    assert 'href="/repo/blog/"' in read(site, "index.html")

    stats = build(site, base_path="")            # how `ctf serve` builds
    assert stats.mode == "full"                  # prefix change busts the cache
    home = read(site, "index.html")
    assert 'href="/blog/"' in home
    assert "/repo" not in home


def test_sitemap_skipped_without_base_url(site: Path, build):
    cfg = site / "config.toml"
    cfg.write_text(cfg.read_text().replace(
        'base_url = "https://example.com"', 'base_url = ""'))
    stats = build(site)
    assert stats.sitemap is False
    assert not (site / "public" / "sitemap.xml").exists()


def test_listing_is_summary_only(site: Path, build):
    """The blog index must NOT contain a post's rendered body."""
    build(site)
    body_marker = "this page was built from a plain text file"  # appears in hello-world body
    assert body_marker in read(site, "blog/hello-world/index.html")
    assert body_marker not in read(site, "blog/index.html")


def test_content_terms_link_to_term_pages(site: Path, build):
    """A post's tags render as links to their term pages."""
    build(site)
    post = read(site, "blog/hello-world/index.html")  # tags = ["meta", "python"]
    assert '<a href="/tags/meta/">meta</a>' in post
    assert '<a href="/tags/python/">python</a>' in post


def test_term_page_shows_item_content_type(site: Path, build):
    """A summary exposes `item.type`, so the term page can label each item with
    its content type (a taxonomy may span types)."""
    build(site)
    term = read(site, "tags/meta/index.html")  # meta tags blog posts
    assert '<span class="content-type">blog</span>' in term


def test_featured_is_a_taxonomy_term(site: Path, build):
    """Curated 'featured' items are just a tag: the term page lists them and the
    home tag cloud links to it — there is no dedicated featured mechanism."""
    build(site)
    featured = read(site, "tags/featured/index.html")
    assert "Front Matter" in featured        # tagged `featured`
    assert "Hello, World" not in featured    # not tagged
    index = read(site, "index.html")
    assert '<a href="/tags/featured/">featured' in index


def test_error_page_built_and_excluded_from_sitemap(site: Path, build):
    """The scaffold's 404.html renders to the site root but stays out of the sitemap."""
    stats = build(site)
    assert stats.error_pages == 1
    page = read(site, "404.html")           # at the root, not a pretty URL
    assert "Page not found" in page          # rendered through base.html
    assert "<title>" in page and "Demo Site" in page  # site-global context available
    # A 404 is a host fallback, not a crawlable page — keep it out of the sitemap.
    assert "404" not in read(site, "sitemap.xml")


def test_pages_have_no_index(site: Path, build):
    build(site)
    # 'pages' is standalone: no /pages/ index is generated.
    assert not (site / "public" / "pages" / "index.html").exists()
    assert (site / "public" / "about" / "index.html").is_file()


def test_check_validates_but_writes_nothing(site: Path):
    stats = _quiet_check(site)
    # The full pipeline ran (content was rendered)...
    assert stats.content > 0
    # ...but nothing landed in the site: no output dir, no cache.
    assert not (site / "public").exists()
    assert not (site / ".ctf").exists()


def test_check_leaves_an_existing_build_untouched(site: Path, build):
    build(site)
    before = _snapshot(site / "public")
    cache_before = (site / ".ctf" / "cache.json").read_bytes()
    _quiet_check(site)
    assert _snapshot(site / "public") == before
    assert (site / ".ctf" / "cache.json").read_bytes() == cache_before


def test_check_catches_content_errors(site: Path):
    # Malformed TOML front matter is a build error — check must surface it.
    page = site / "content" / "pages" / "about.md"
    page.write_text(page.read_text().replace("+++\n", "+++\ntitle = = broken\n", 1), encoding="utf-8")
    with pytest.raises(ContentError):
        _quiet_check(site)


def test_check_catches_config_errors(site: Path):
    # An unknown top-level table is rejected by config validation.
    config = site / "config.toml"
    config.write_text(config.read_text() + "\n[bogus_table]\nx = 1\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        _quiet_check(site)
