"""End-to-end full-build tests against the scaffolded site."""

from __future__ import annotations

from pathlib import Path

from tests.conftest import read


def test_full_build_outputs(site: Path, build):
    stats = build(site)
    public = site / "public"
    for rel in [
        "index.html",
        "blog/index.html",
        "blog/hello-world/index.html",
        "projects/index.html",
        "projects/cuttlefish/index.html",
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
    body_marker = "cuttlefish builds this with mistune"  # appears in hello-world body
    assert body_marker in read(site, "blog/hello-world/index.html")
    assert body_marker not in read(site, "blog/index.html")


def test_content_terms_link_to_term_pages(site: Path, build):
    """A post's tags render as links to their term pages."""
    build(site)
    post = read(site, "blog/hello-world/index.html")  # tags = ["meta", "python"]
    assert '<a href="/tags/meta/">meta</a>' in post
    assert '<a href="/tags/python/">python</a>' in post


def test_pages_have_no_index(site: Path, build):
    build(site)
    # 'pages' is standalone: no /pages/ index is generated.
    assert not (site / "public" / "pages" / "index.html").exists()
    assert (site / "public" / "about" / "index.html").is_file()
