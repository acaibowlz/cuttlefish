"""Unit tests for `taxonomy.py`: term grouping and ordering."""

from __future__ import annotations

from cuttlefish.config import parse_config
from cuttlefish.taxonomy import Term, TaxonomyData, home_taxonomy_terms


def test_taxonomy_term_ordering():
    def ordered(sort_by, order):
        cfg = parse_config(
            {
                "taxonomies": {
                    "tags": {
                        "template": "t.html",
                        "permalink": "/t/{term}/",
                        "sort_by": sort_by,
                        "order": order,
                    }
                }
            }
        )
        data = TaxonomyData(taxonomy=cfg.taxonomies["tags"])
        for name, n in [("python", 3), ("meta", 3), ("ssg", 7)]:
            term = Term(
                taxonomy="tags", name=name, url=f"/t/{name}/", output_rel=f"t/{name}/index.html"
            )
            term.items = list(range(n))
            data.terms[name] = term
        # sorted_terms (index page) and home_taxonomy_terms (home list) agree.
        assert [t.name for t in data.sorted_terms] == [t.name for t in home_taxonomy_terms(data)]
        return [t.name for t in data.sorted_terms]

    # count/desc: most-used first, alphabetical tiebreak for the two 3s.
    assert ordered("count", "desc") == ["ssg", "meta", "python"]
    assert ordered("name", "asc") == ["meta", "python", "ssg"]
    assert ordered("name", "desc") == ["ssg", "python", "meta"]
