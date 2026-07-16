"""Incremental-build correctness: the Milestone 2 dependency graph.

The scaffolded site has 4 content files (2 blog, 1 project, 1 page) and 6
aggregates: index:blog, index:project, taxonomy:tags:meta, taxonomy:tags:python,
taxonomy_index:tags, home.
"""

from __future__ import annotations

from pathlib import Path

from tests.conftest import append

# Scaffold aggregates: home, the blog + project indexes, the tags index, and the
# three tag term pages (meta, python, featured).
TOTAL_AGGREGATES = 7


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not found in {path}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def _snapshot(public: Path) -> dict[str, bytes]:
    """Map every output file (rel path) to its bytes, for equality checks."""
    return {
        str(p.relative_to(public)): p.read_bytes()
        for p in public.rglob("*")
        if p.is_file()
    }


def test_incremental_output_matches_full(site: Path, build):
    # The core invariant behind having one build path: a series of incremental
    # rebuilds must leave public/ byte-identical to a full build of the same
    # final source. Exercise content edits, a new tag (aggregates), a new file,
    # and a deletion (pruning), then compare to a forced full rebuild.
    build(site)
    _edit(site / "content/blog/hello-world.md", 'title = "Hello, World"', 'title = "Hi"')
    _edit(site / "content/blog/second-post.md", 'tags = ["meta", "featured"]', 'tags = ["meta", "featured", "news"]')
    (site / "content/project/example-project.md").unlink()
    (site / "content/blog/fresh.md").write_text(
        '+++\ntitle = "Fresh"\ndate = 2026-07-01\n'
        'description = "A new post."\ntags = ["news"]\n+++\n\nBody.\n',
        encoding="utf-8",
    )
    build(site)  # fold all of the above in via the incremental path
    incremental = _snapshot(site / "public")

    stats = build(site, force=True)
    assert stats.mode == "full"
    full = _snapshot(site / "public")

    assert incremental == full


def test_a_body_edit_skips_all_aggregates(site: Path, build):
    build(site)
    append(site / "content/blog/hello-world.md", "\nA new paragraph.\n")
    stats = build(site)
    assert stats.mode == "incremental"
    assert stats.content == 1
    assert stats.skipped == 3
    assert stats.indexes == 0
    assert stats.terms == 0
    assert stats.aggregates_skipped == TOTAL_AGGREGATES


def test_b_title_edit_rebuilds_listings(site: Path, build):
    build(site)
    _edit(site / "content/blog/hello-world.md",
          'title = "Hello, World"', 'title = "Hello, Universe"')
    stats = build(site)
    assert stats.content == 1
    assert stats.indexes == 1          # blog index
    assert stats.terms == 2            # meta + python (both contain the post)
    assert stats.home == 1             # post is in "recent"
    assert stats.taxonomy_indexes == 0  # term set/counts unchanged


def test_c_new_tag_rebuilds_taxonomy_index_and_new_term(site: Path, build):
    build(site)
    _edit(site / "content/blog/hello-world.md",
          'tags = ["meta", "python"]', 'tags = ["meta", "python", "fresh"]')
    stats = build(site)
    assert stats.taxonomy_indexes == 1
    assert (site / "public/tags/fresh/index.html").is_file()


def test_d_base_template_forces_all(site: Path, build):
    build(site)
    append(site / "templates/base.html", "\n<!-- edit -->\n")
    stats = build(site)
    assert stats.content == 4
    assert stats.aggregates_skipped == 0
    assert stats.error_pages == 1      # 404 extends base.html, so it re-renders too


def test_e_config_change_forces_full(site: Path, build):
    build(site)
    append(site / "config.toml", "\n# a comment\n")
    stats = build(site)
    assert stats.mode == "full"


def test_f_delete_prunes_output(site: Path, build):
    build(site)
    assert (site / "public/blog/front-matter/index.html").is_file()
    (site / "content/blog/second-post.md").unlink()
    stats = build(site)
    assert stats.pruned >= 1
    assert not (site / "public/blog/front-matter/index.html").exists()


def test_g_slug_rename_prunes_old_writes_new(site: Path, build):
    build(site)
    assert (site / "public/blog/hello-world/index.html").is_file()
    _edit(site / "content/blog/hello-world.md",
          'title = "Hello, World"', 'title = "Hello, World"\nslug = "hi"')
    stats = build(site)
    assert stats.pruned >= 1
    assert (site / "public/blog/hi/index.html").is_file()
    assert not (site / "public/blog/hello-world/index.html").exists()


def test_h_error_page_rebuilds_in_isolation(site: Path, build):
    # Editing 404.html re-renders only the error page: it backs no content type
    # and no aggregate, so nothing else is touched.
    build(site)
    append(site / "templates/404.html", "\n<!-- edit -->\n")
    stats = build(site)
    assert stats.mode == "incremental"
    assert stats.error_pages == 1
    assert stats.content == 0
    assert stats.aggregates_skipped == TOTAL_AGGREGATES


def test_i_error_template_removed_prunes_output(site: Path, build):
    build(site)
    assert (site / "public/404.html").is_file()
    (site / "templates/404.html").unlink()
    stats = build(site)
    assert stats.pruned >= 1
    assert not (site / "public/404.html").exists()


def test_no_change_skips_everything(site: Path, build):
    build(site)
    stats = build(site)
    assert stats.content == 0
    assert stats.skipped == 4
    assert stats.aggregates_skipped == TOTAL_AGGREGATES
    assert stats.error_pages == 0      # unchanged 404 template is not re-rendered
