"""Incremental-build correctness: the Milestone 2 dependency graph.

The scaffolded site has 4 content files (2 blog, 1 project, 1 page) and 6
aggregates: index:blog, index:project, taxonomy:tags:meta, taxonomy:tags:python,
taxonomy_index:tags, home.
"""

from __future__ import annotations

from pathlib import Path

from tests.conftest import append

TOTAL_AGGREGATES = 6


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not found in {path}"
    path.write_text(text.replace(old, new), encoding="utf-8")


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


def test_no_change_skips_everything(site: Path, build):
    build(site)
    stats = build(site)
    assert stats.content == 0
    assert stats.skipped == 4
    assert stats.aggregates_skipped == TOTAL_AGGREGATES
