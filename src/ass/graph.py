"""Milestone 2: dependency graph for precise aggregate rebuilds.

An *aggregate* is any page that lists multiple content items: a type index, a
taxonomy term page, a taxonomy index, or the home page. Each aggregate gets:

- a stable **key** (e.g. ``index:blog``, ``taxonomy:tags:python``),
- a **fingerprint** over exactly the data it renders (member listing
  fingerprints, term counts, …) — never content bodies,
- the **template** it uses, and
- a **render** callable plus its expected **outputs**.

An aggregate is rebuilt only when its fingerprint changed or its template was
(transitively) affected by a template edit. Everything else is skipped.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from ass.cache import hash_text
from ass.config import SiteConfig
from ass.content import ContentItem
from ass.render import Renderer
from ass.taxonomy import TaxonomyData


@dataclass
class AggregateSpec:
    """A renderable aggregate page and the inputs that determine its output."""

    key: str
    template: str
    fingerprint: str
    outputs: list[str]
    render: Callable[[], list[str]]


def _members_fingerprint(items: list[ContentItem], extra: str = "") -> str:
    payload = [i.meta_fingerprint for i in items]
    return hash_text(json.dumps(payload) + "::" + extra)


def build_aggregate_specs(
    config: SiteConfig,
    grouped: dict[str, list[ContentItem]],
    taxonomies: dict[str, TaxonomyData],
    renderer: Renderer,
) -> list[AggregateSpec]:
    """Enumerate every aggregate page as a spec (no rendering happens here)."""
    specs: list[AggregateSpec] = []

    # Type indexes.
    for name, content_type in config.content_types.items():
        if not content_type.has_index:
            continue
        items = grouped.get(name, [])
        specs.append(
            AggregateSpec(
                key=f"index:{name}",
                template=content_type.index_template,  # type: ignore[arg-type]
                fingerprint=_members_fingerprint(items, f"paginate={content_type.paginate}"),
                outputs=renderer.index_output_rels(content_type, len(items)),
                render=(lambda ct=content_type, it=items: renderer.render_index(ct, it)),
            )
        )

    # Taxonomy term pages + taxonomy indexes.
    for tax_name, data in taxonomies.items():
        for term_name, term in data.terms.items():
            specs.append(
                AggregateSpec(
                    key=f"taxonomy:{tax_name}:{term_name}",
                    template=data.taxonomy.template,
                    fingerprint=_members_fingerprint(term.items),
                    outputs=[term.output_rel],
                    render=(lambda d=data, t=term: [renderer.render_term(d, t)]),
                )
            )
        if data.taxonomy.has_index and data.index_output_rel is not None:
            terms_fp = hash_text(
                json.dumps(
                    [(t.name, t.count) for t in data.sorted_terms], sort_keys=True
                )
            )
            specs.append(
                AggregateSpec(
                    key=f"taxonomy_index:{tax_name}",
                    template=data.taxonomy.index_template,  # type: ignore[arg-type]
                    fingerprint=terms_fp,
                    outputs=[data.index_output_rel],
                    render=(lambda d=data: [renderer.render_taxonomy_index(d)]),
                )
            )

    # Home.
    home = config.home
    if home is not None:
        recent = {
            type_name: grouped.get(type_name, [])[:count]
            for type_name, count in home.recent.items()
        }
        # Fingerprint over every section's items, salted with the section names
        # (and their order), so adding/reordering a section also rebuilds home.
        members = [item for items in recent.values() for item in items]
        specs.append(
            AggregateSpec(
                key="home",
                template=home.template,
                fingerprint=_members_fingerprint(members, "home:" + ",".join(recent)),
                outputs=["index.html"],
                render=(lambda r=recent: [x for x in [renderer.render_home(r)] if x]),
            )
        )

    return specs


def aggregate_is_dirty(
    spec: AggregateSpec,
    previous: dict[str, dict],
    affected_templates: set[str],
) -> bool:
    """Decide whether *spec* must be re-rendered this build."""
    old = previous.get(spec.key)
    if old is None:
        return True
    if old.get("fingerprint") != spec.fingerprint:
        return True
    if spec.template in affected_templates:
        return True
    return False
