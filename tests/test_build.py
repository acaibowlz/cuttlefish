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
        "projects/ass/index.html",
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


def test_listing_is_summary_only(site: Path, build):
    """The blog index must NOT contain a post's rendered body."""
    build(site)
    body_marker = "ass builds this with mistune"  # appears in hello-world body
    assert body_marker in read(site, "blog/hello-world/index.html")
    assert body_marker not in read(site, "blog/index.html")


def test_pages_have_no_index(site: Path, build):
    build(site)
    # 'pages' is standalone: no /pages/ index is generated.
    assert not (site / "public" / "pages" / "index.html").exists()
    assert (site / "public" / "about" / "index.html").is_file()
