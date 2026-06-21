"""Build taxonomy term -> items mappings from parsed content.

For each configured taxonomy (e.g. ``tags``), we collect every term used across
content and which items carry it, then resolve each term's page URL and the
taxonomy index URL.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ass.config import SiteConfig, Taxonomy
from ass.content import ContentItem
from ass.permalink import resolve_permalink, slugify


@dataclass
class Term:
    """A single taxonomy term (e.g. tag "python") and the items under it."""

    taxonomy: str
    name: str
    url: str
    output_rel: str
    items: list[ContentItem] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.items)


@dataclass
class TaxonomyData:
    """All terms of one taxonomy, plus its index location."""

    taxonomy: Taxonomy
    terms: dict[str, Term] = field(default_factory=dict)
    index_url: str | None = None
    index_output_rel: str | None = None

    @property
    def sorted_terms(self) -> list[Term]:
        return sorted(self.terms.values(), key=lambda t: t.name.lower())


def _output_rel(url: str) -> str:
    rel = url.lstrip("/")
    if url.endswith("/") or rel == "":
        rel += "index.html"
    return rel


def build_taxonomies(items: list[ContentItem], config: SiteConfig) -> dict[str, TaxonomyData]:
    """Group *items* by every configured taxonomy term."""
    result: dict[str, TaxonomyData] = {}
    for name, taxonomy in config.taxonomies.items():
        data = TaxonomyData(taxonomy=taxonomy)
        if taxonomy.has_index:
            data.index_url = resolve_permalink(taxonomy.index_permalink, taxonomy=name)
            data.index_output_rel = _output_rel(data.index_url)
        result[name] = data

    for item in items:
        for tax_name, terms in item.taxonomies.items():
            data = result.get(tax_name)
            if data is None:
                continue
            for term_name in terms:
                term = data.terms.get(term_name)
                if term is None:
                    url = resolve_permalink(
                        data.taxonomy.permalink,
                        taxonomy=tax_name,
                        term=slugify(term_name),
                    )
                    term = Term(
                        taxonomy=tax_name,
                        name=term_name,
                        url=url,
                        output_rel=_output_rel(url),
                    )
                    data.terms[term_name] = term
                term.items.append(item)
    return result
