"""Discover and parse Markdown content files.

Each content file lives at ``content/<type>/<name>.md`` (or
``content/pages/<name>.md``) and begins with a TOML front-matter block fenced
by ``+++`` lines, followed by a Markdown body:

    +++
    title = "Hello"
    date = 2026-06-21
    tags = ["python"]
    +++
    # Body in Markdown

Parsing yields :class:`ContentItem` objects with the body already rendered to
HTML. Aggregates (indexes, taxonomy pages, home) receive a restricted
:class:`ContentSummary` view that deliberately omits ``body_html`` — this keeps
incremental builds correct (a body-only edit cannot affect any listing).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import mistune
from mistune.toc import normalize_toc_item

from cuttlefish.config import PAGES_TYPE, SiteConfig
from cuttlefish.errors import CuttlefishError
from cuttlefish.permalink import resolve_permalink, slugify

CONTENT_DIR = "content"
FRONT_MATTER_FENCE = "+++"

#: The fields that make up a content summary — everything an aggregate/listing
#: template is allowed to render; ``body_html`` is intentionally excluded.
SUMMARY_FIELDS = (
    "type",
    "title",
    "date",
    "description",
    "cover",
    "slug",
    "url",
    "taxonomies",
    "draft",
)

#: Front-matter keys promoted to typed :class:`ContentItem` fields. They are
#: read as attributes (never a raw dict), excluded from the free-form
#: ``params``, and — because each is always present with a default — always
#: available as a ``sort_by`` target.
_PROMOTED_KEYS = frozenset({"title", "description", "date", "slug", "draft", "cover"})


@dataclass(frozen=True)
class TocEntry:
    """One heading in a body's table of contents, ready to link to."""

    level: int  # 1-6, matching the heading tag (h1..h6)
    id: str  # slug set as the heading's ``id`` attribute in ``body_html``
    text: str  # plain-text heading label (inline markup stripped)

    @property
    def url(self) -> str:
        """In-page anchor to the heading, e.g. ``#getting-started``."""
        return f"#{self.id}"


def _toc_hook(md: mistune.Markdown, state: mistune.core.BlockState) -> None:
    """Give every heading a stable slug ``id`` and collect the TOC.

    Runs before rendering so the ``id`` we assign lands in ``body_html`` *and*
    in the collected entries, keeping anchor links and TOC targets in lockstep.
    Slugs come from the heading text (not an opaque counter) so anchors stay
    readable and stable across edits; duplicates get a ``-1``, ``-2`` suffix so
    every ``id`` is unique within a page. ``seen`` is local to this call, so the
    numbering resets per document even though the hook is shared.
    """
    seen: dict[str, int] = {}
    entries: list[TocEntry] = []
    for tok in state.tokens:
        if tok["type"] != "heading":
            continue
        base = slugify(tok["text"])
        n = seen.get(base, 0)
        seen[base] = n + 1
        tok["attrs"]["id"] = base if n == 0 else f"{base}-{n}"
        level, hid, text = normalize_toc_item(md, tok, parent=state)
        entries.append(TocEntry(level=level, id=hid, text=text))
    state.env["toc"] = entries


# `mark` and `math` only emit markup — `<mark>…</mark>` and
# `<span class="math">\(…\)</span>` / `<div class="math">$$…$$</div>`. `mark`
# renders on its own (browsers style `<mark>`); `math` needs a MathJax/KaTeX
# script the *site* supplies, which is why we ship no such JS by default (see the
# scaffold AGENTS.md). Enabling the parser side here costs nothing until a page
# uses it and keeps the generator free of any client-side dependency.
_markdown = mistune.create_markdown(
    escape=False,
    plugins=["table", "footnotes", "strikethrough", "task_lists", "url", "mark", "math"],
)
_markdown.before_render_hooks.append(_toc_hook)


def render_markdown(body: str) -> tuple[str, list[TocEntry]]:
    """Render a Markdown body to HTML plus its table of contents."""
    html, state = _markdown.parse(body)
    return html, state.env.get("toc", [])


class ContentError(CuttlefishError):
    """Raised when a content file cannot be parsed."""

    default_summary = "Failed to parse content"


@dataclass(frozen=True)
class ContentSummary:
    """Reduced view of a :class:`ContentItem` for listing/aggregate templates.

    Carries only the fields safe to show without the body (:data:`SUMMARY_FIELDS`),
    never ``body_html``. That omission is what keeps incremental builds correct.
    """

    type: str
    title: str
    date: date | None
    description: str
    cover: str
    slug: str
    url: str
    taxonomies: dict[str, list[str]]
    draft: bool


@dataclass
class ContentItem:
    """A single parsed content file, with its body rendered to HTML."""

    type: str
    slug: str
    #: Front-matter fields the generator understands, promoted to typed
    #: attributes at parse time. The dataclass is the boundary of truth, so
    #: downstream code reads a field, never ``meta.get(...)``.
    title: str
    description: str
    date: date | None
    draft: bool
    #: Optional cover/hero image URL (e.g. ``/img/post.jpg``). A summary field, so
    #: listings can show a thumbnail; empty string when unset.
    cover: str
    body_html: str
    taxonomies: dict[str, list[str]]
    #: Free-form front-matter fields: everything that is neither a promoted
    #: field nor a configured taxonomy. Exposed to full-item templates as
    #: ``page.params`` — the per-page counterpart to ``site.params``.
    params: dict
    source_rel: str  # path relative to site root, e.g. "content/blog/post.md"
    url: str
    output_rel: str  # path relative to public/, e.g. "blog/post/index.html"
    #: Body headings as a flat, in-order list; single-content templates read it
    #: to build a table of contents. Empty for bodies with no headings.
    toc: list[TocEntry] = field(default_factory=list)

    def sort_value(self, key: str) -> object:
        """Value used to order items when a content type's ``sort_by`` names *key*.

        A promoted field resolves to its typed value; anything else falls back
        to ``params``, so ``sort_by`` can point at a custom front-matter field
        (e.g. a Hugo-style ``weight``) as readily as at ``title``.
        """
        if key in _PROMOTED_KEYS:
            return getattr(self, key)
        return self.params.get(key)

    def has_sort_field(self, key: str) -> bool:
        """Whether *key* is a field this item carries (promoted or custom).

        Lets the build flag a ``sort_by`` that matches nothing — almost always
        a typo. Promoted fields always count; custom ones must be in ``params``.
        """
        return key in _PROMOTED_KEYS or key in self.params

    @property
    def meta_fingerprint(self) -> str:
        """Hash of the summary fields only (never the body).

        Used by aggregates to decide whether one must be rebuilt: a body-only
        edit leaves this unchanged, so indexes are correctly skipped.
        """
        import json

        from cuttlefish.cache import hash_text

        payload = {
            "type": self.type,
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "description": self.description,
            "cover": self.cover,
            "slug": self.slug,
            "url": self.url,
            "taxonomies": {k: sorted(v) for k, v in sorted(self.taxonomies.items())},
            "draft": self.draft,
        }
        return hash_text(json.dumps(payload, sort_keys=True))

    @property
    def summary(self) -> ContentSummary:
        return ContentSummary(
            type=self.type,
            title=self.title,
            date=self.date,
            description=self.description,
            cover=self.cover,
            slug=self.slug,
            url=self.url,
            taxonomies=self.taxonomies,
            draft=self.draft,
        )


def split_front_matter(text: str) -> tuple[dict, str]:
    """Split ``+++`` TOML front matter from the Markdown body."""
    stripped = text.lstrip("﻿")  # tolerate a BOM
    if not stripped.startswith(FRONT_MATTER_FENCE):
        return {}, text
    lines = stripped.splitlines(keepends=True)
    # Find the closing fence after the opening one.
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONT_MATTER_FENCE:
            closing = i
            break
    if closing is None:
        raise ContentError("Front matter opened with '+++' but never closed.")
    fm_text = "".join(lines[1:closing])
    body = "".join(lines[closing + 1 :])
    try:
        meta = tomllib.loads(fm_text)
    except tomllib.TOMLDecodeError as exc:
        raise ContentError(f"Invalid TOML front matter: {exc}") from exc
    return meta, body


def _require_front_matter(meta: dict, type_name: str, config: SiteConfig, err_summary: str) -> None:
    """Enforce required front matter.

    Regular content (blog, project, …) must declare ``title``, ``description``
    and a ``date``. A standalone ``pages`` file needs only a ``title`` (for its
    heading and ``<title>``) and its filename-derived slug — it carries no date
    and no description requirement.

    A page is never grouped into a type index or a taxonomy listing, so a
    configured taxonomy key on it does nothing structural — yet it would still
    pull the page into that taxonomy's term pages (an "About" page surfacing
    under ``/tags/``). That silent surprise is worse than an error, so a taxonomy
    key on a page is rejected.

    ``date`` must be a plain ``YYYY-MM-DD`` value: an unquoted TOML *local date*
    (``date = 2026-07-02``), not a quoted string and not a date-time. The TOML
    parser validates the calendar date for us, this avoids the silent trap where
    a quoted date is ignored entirely, and rejecting a time component keeps every
    post's date to a single, sortable day.
    """
    if type_name == PAGES_TYPE:
        if not str(meta.get("title", "")).strip():
            raise ContentError("Missing required front-matter 'title'.", summary=err_summary)
        for name in config.taxonomies:
            if name in meta:
                raise ContentError(
                    f"Standalone pages cannot set the '{name}' taxonomy — a page is "
                    "not part of any taxonomy listing. Remove it.",
                    summary=err_summary,
                )
        return
    for key in ("title", "description"):
        if not str(meta.get(key, "")).strip():
            raise ContentError(f"Missing required front-matter '{key}'.", summary=err_summary)
    if "date" not in meta:
        raise ContentError("Missing required front-matter 'date'.", summary=err_summary)
    value = meta["date"]
    # datetime is a subclass of date, so check it first: a date-time has a time
    # component we don't want. What remains must be a plain date (not a string).
    if isinstance(value, datetime):
        raise ContentError(
            "Front-matter 'date' must be a plain YYYY-MM-DD date (e.g. 2026-07-02), "
            "without a time component.",
            summary=err_summary,
        )
    if not isinstance(value, date):
        raise ContentError(
            "Front-matter 'date' must be an unquoted YYYY-MM-DD date "
            f"(e.g. 2026-07-02), got {type(value).__name__}.",
            summary=err_summary,
        )


def _coerce_date(value: object) -> date | None:
    """Front-matter date as a plain ``date`` (a datetime is narrowed to its day)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _custom_params(meta: dict, config: SiteConfig) -> dict:
    """Free-form front matter: everything not promoted and not a taxonomy key."""
    reserved = _PROMOTED_KEYS | set(config.taxonomies)
    return {key: value for key, value in meta.items() if key not in reserved}


def _extract_taxonomies(meta: dict, config: SiteConfig) -> dict[str, list[str]]:
    """Pull configured-taxonomy terms out of the front matter."""
    result: dict[str, list[str]] = {}
    for name, taxonomy in config.taxonomies.items():
        value = meta.get(name)
        if value is None:
            continue
        if taxonomy.multiple:
            if not isinstance(value, (list, tuple)):
                raise ContentError(
                    f"Taxonomy '{name}' expects a list of terms (multiple = true), "
                    f"got {type(value).__name__}."
                )
            terms = [str(v) for v in value]
        else:
            if not isinstance(value, str):
                raise ContentError(
                    f"Taxonomy '{name}' expects a single term (multiple = false), "
                    f"got {type(value).__name__}."
                )
            terms = [value]
        result[name] = [t for t in terms if t]
    return result


def parse_item(path: Path, type_name: str, config: SiteConfig) -> ContentItem:
    """Parse a single content file into a :class:`ContentItem`."""
    text = path.read_text(encoding="utf-8")
    summary = f"Failed to parse {_relative_to_root(path, config)}"
    try:
        meta, body = split_front_matter(text)
    except ContentError as exc:
        raise ContentError(exc.detail, summary=summary) from exc

    _require_front_matter(meta, type_name, config, summary)

    slug = str(meta.get("slug") or slugify(path.stem))
    body_html, toc = render_markdown(body)
    taxonomies = _extract_taxonomies(meta, config)

    content_type = config.content_types[type_name]
    item_date = meta.get("date")
    url = resolve_permalink(
        content_type.permalink,
        date=item_date,
        slug=slug,
        type=type_name,
    )
    output_rel = url.lstrip("/")
    if url.endswith("/") or output_rel == "":
        output_rel = output_rel + "index.html"

    source_rel = _relative_to_root(path, config)
    return ContentItem(
        type=type_name,
        slug=slug,
        title=str(meta.get("title", slug)),
        description=str(meta.get("description", "")),
        date=_coerce_date(item_date),
        draft=bool(meta.get("draft", False)),
        cover=str(meta.get("cover", "")),
        body_html=body_html,
        taxonomies=taxonomies,
        params=_custom_params(meta, config),
        source_rel=source_rel,
        url=url,
        output_rel=output_rel,
        toc=toc,
    )


def _relative_to_root(path: Path, config: SiteConfig) -> str:
    # config.raw doesn't carry the root; callers pass absolute paths under root.
    # We store a content-relative path that's stable for the manifest.
    parts = path.parts
    if CONTENT_DIR in parts:
        idx = parts.index(CONTENT_DIR)
        return "/".join(parts[idx:])
    return path.name


def discover(root: Path, config: SiteConfig, *, drafts: bool = False) -> list[ContentItem]:
    """Find and parse all content files under ``<root>/content``."""
    content_root = root / CONTENT_DIR
    items: list[ContentItem] = []
    if not content_root.is_dir():
        return items

    for type_name in config.content_types:
        type_dir = content_root / type_name
        if not type_dir.is_dir():
            continue
        for md in sorted(type_dir.rglob("*.md")):
            item = parse_item(md, type_name, config)
            if item.draft and not drafts:
                continue
            items.append(item)
    return items


def sort_items(
    items: list[ContentItem], *, sort_by: str = "date", order: str = "desc"
) -> list[ContentItem]:
    """Return *items* sorted by a front-matter field (missing values last)."""

    def key(item: ContentItem):
        if sort_by == "date":
            return (item.date is not None, item.date or date.min)
        value = item.sort_value(sort_by)
        return (value is not None, value if value is not None else "")

    return sorted(items, key=key, reverse=(order == "desc"))
