"""Build taxonomy term -> items mappings from parsed content.

For each configured taxonomy (e.g. ``tags``), we collect every term used across
content and which items carry it, then resolve each term's page URL and the
taxonomy index URL.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cuttlefish.config import ConfigError, SiteConfig, Taxonomy
from cuttlefish.content import ContentItem, sort_items
from cuttlefish.permalink import resolve_permalink, slugify


@dataclass(frozen=True)
class TermLink:
    """A term resolved to its page URL, for linking from content templates."""

    name: str
    url: str


@dataclass(frozen=True)
class HomeTerm:
    """A taxonomy term exposed on the landing page (name, item count, URL)."""

    name: str
    count: int
    url: str


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
        """Terms ordered per the taxonomy's ``sort_by``/``order`` config.

        Name is always the tiebreaker (ascending), so equal-count terms stay in
        a stable, readable order regardless of the primary sort. This single
        ordering is used everywhere terms are listed — the term index page and
        the home-page term list — so both agree.
        """
        taxonomy = self.taxonomy
        terms = sorted(self.terms.values(), key=lambda t: t.name.lower())
        if taxonomy.sort_by == "count":
            terms.sort(key=lambda t: t.count, reverse=taxonomy.descending)
        elif taxonomy.descending:
            terms.reverse()
        return terms


def _output_rel(url: str) -> str:
    rel = url.lstrip("/")
    if url.endswith("/") or rel == "":
        rel += "index.html"
    return rel


def term_links(item: ContentItem, config: SiteConfig) -> dict[str, list[TermLink]]:
    """Resolve an item's taxonomy terms to ``{name, url}`` links.

    Lets single-content templates render each term as a link to its term page
    (e.g. ``/tags/python/``) without hard-coding permalink patterns. The URL is
    derived purely from the taxonomy's configured permalink, so it matches the
    page :func:`build_taxonomies` emits for that term.
    """
    links: dict[str, list[TermLink]] = {}
    for tax_name, terms in item.taxonomies.items():
        taxonomy = config.taxonomies.get(tax_name)
        if taxonomy is None:
            continue
        links[tax_name] = [
            TermLink(
                name=term_name,
                url=resolve_permalink(
                    taxonomy.permalink, taxonomy=tax_name, term=slugify(term_name)
                ),
            )
            for term_name in terms
        ]
    return links


def home_taxonomy_terms(data: TaxonomyData) -> list[HomeTerm]:
    """Home-page ``HomeTerm`` views of a taxonomy's terms.

    Reuses :attr:`TaxonomyData.sorted_terms` so the home list and the term
    index page share one ordering (the taxonomy's ``sort_by``/``order``).
    """
    return [HomeTerm(name=t.name, count=t.count, url=t.url) for t in data.sorted_terms]


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

    # Order each term page's items by the taxonomy's item sort. `sort_by` is
    # open-ended (any front-matter field), so — as with a content type — a key
    # present on none of a taxonomy's items is almost certainly a typo; surface
    # it rather than leave the page in discovery (filename) order. `date` is
    # always valid, even for a taxonomy with no items yet.
    for name, data in result.items():
        taxonomy = data.taxonomy
        members = [item for term in data.terms.values() for item in term.items]
        if (
            members
            and taxonomy.item_sort_by != "date"
            and not any(item.has_sort_field(taxonomy.item_sort_by) for item in members)
        ):
            raise ConfigError(
                f"[taxonomies.{name}.items] 'sort_by' = {taxonomy.item_sort_by!r} is not a "
                f'field on any item under this taxonomy. Use "date" or a front-matter '
                "field present on your items."
            )
        for term in data.terms.values():
            term.items = sort_items(
                term.items, sort_by=taxonomy.item_sort_by, order=taxonomy.item_order
            )
    return result
