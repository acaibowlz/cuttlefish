"""Load and validate ``config.toml`` into typed dataclasses.

The whole site is described by a single ``config.toml`` at the site root. This
module turns it into ``SiteConfig`` (plus ``ContentType``, ``Taxonomy``,
``HomeConfig``) and validates it, raising :class:`ConfigError` with a clear
message an agent can act on.
"""

from __future__ import annotations

import difflib
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from ass.errors import AssError

#: The content type name reserved for standalone pages (no index, no taxonomy).
PAGES_TYPE = "pages"

CONFIG_FILENAME = "config.toml"

#: Where config errors point users for the full key reference.
#: TODO: update to the published Configuration docs page once it is hosted.
CONFIG_DOCS_URL = "https://example.com/ass/configuration"

#: Allowed keys for each strictly-validated config scope. Unknown keys are
#: rejected — they are almost always typos that would otherwise be silently
#: ignored. Custom/free-form values are not supported at the moment.
_TOP_LEVEL_KEYS = frozenset({"title", "base_url", "content_types", "taxonomies", "home", "nav"})
_CONTENT_TYPE_KEYS = frozenset(
    {"template", "permalink", "index_template", "index_permalink", "paginate", "sort_by", "order"}
)
_TAXONOMY_KEYS = frozenset({"template", "permalink", "index_template", "index_permalink"})
_HOME_KEYS = frozenset({"template", "recent"})
_HOME_RECENT_KEYS = frozenset({"type", "count"})
_NAV_KEYS = frozenset({"enabled", "labels", "links"})


class ConfigError(AssError):
    """Raised when ``config.toml`` is missing or invalid."""

    default_summary = "Failed to load config"


def _reject_unknown_keys(data: dict, allowed: frozenset[str], where: str) -> None:
    """Raise on the first key in *data* that is not in *allowed* (file order)."""
    for key in data:
        if key not in allowed:
            match = difflib.get_close_matches(key, sorted(allowed), n=1)
            # Put the docs pointer on its own line only when there's also a
            # suggestion; otherwise keep the whole message on one line.
            suffix = f" Did you mean {match[0]!r}?\n" if match else " "
            raise ConfigError(
                f"{where} unknown key {key!r}.{suffix}See {CONFIG_DOCS_URL} for valid keys."
            )


@dataclass(frozen=True)
class ContentType:
    """A category of content (e.g. blog, project) with its own templates."""

    name: str
    template: str
    permalink: str
    index_template: str | None = None
    index_permalink: str | None = None
    paginate: int = 0
    sort_by: str = "date"
    order: str = "desc"  # "desc" (newest/largest first) or "asc"

    @property
    def descending(self) -> bool:
        return self.order == "desc"

    @property
    def has_index(self) -> bool:
        return self.index_template is not None and self.index_permalink is not None


@dataclass(frozen=True)
class Taxonomy:
    """A user-defined classification (e.g. tags) applied via front matter."""

    name: str
    template: str
    permalink: str
    index_template: str | None = None
    index_permalink: str | None = None

    @property
    def has_index(self) -> bool:
        return self.index_template is not None and self.index_permalink is not None


@dataclass(frozen=True)
class HomeConfig:
    """The landing page configuration."""

    template: str
    #: Optional aggregation: {"type": "blog", "count": 5} -> recent items.
    recent_type: str | None = None
    recent_count: int = 5


@dataclass(frozen=True)
class NavItem:
    """A single navigation entry (label + link), exposed to templates."""

    label: str
    link: str


@dataclass(frozen=True)
class NavConfig:
    """Site navigation, paired from the ``labels`` and ``links`` arrays."""

    enabled: bool = False
    items: tuple[NavItem, ...] = ()


@dataclass(frozen=True)
class SiteConfig:
    """The whole site configuration, parsed from ``config.toml``."""

    title: str
    base_url: str
    home: HomeConfig | None
    nav: NavConfig = field(default_factory=NavConfig)
    content_types: dict[str, ContentType] = field(default_factory=dict)
    taxonomies: dict[str, Taxonomy] = field(default_factory=dict)
    #: Raw config dict, exposed to templates as ``site.config``.
    raw: dict = field(default_factory=dict)

    @property
    def pages_type(self) -> ContentType | None:
        return self.content_types.get(PAGES_TYPE)


def _require(mapping: dict, key: str, where: str) -> object:
    if key not in mapping:
        raise ConfigError(f"Missing required key '{key}' in {where}.")
    return mapping[key]


def _parse_content_type(name: str, data: dict) -> ContentType:
    where = f"[content_types.{name}]"
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must be a table.")
    _reject_unknown_keys(data, _CONTENT_TYPE_KEYS, where)
    order = str(data.get("order", "desc")).lower()
    if order not in ("asc", "desc"):
        raise ConfigError(f"{where} 'order' must be \"asc\" or \"desc\", got {order!r}.")
    # Only an omitted key or a non-negative integer is valid; 0 (or omitting it)
    # disables pagination. Reject everything else — including bools, which TOML
    # parses as a subclass of int — with a clear message instead of a traceback.
    paginate = data.get("paginate", 0)
    if isinstance(paginate, bool) or not isinstance(paginate, int) or paginate < 0:
        raise ConfigError(
            f"{where} 'paginate' must be a non-negative integer "
            f"(omit it or use 0 to disable pagination), got {paginate!r}."
        )
    return ContentType(
        name=name,
        template=str(_require(data, "template", where)),
        permalink=str(_require(data, "permalink", where)),
        index_template=data.get("index_template"),
        index_permalink=data.get("index_permalink"),
        paginate=paginate,
        sort_by=str(data.get("sort_by", "date")),
        order=order,
    )


def _parse_taxonomy(name: str, data: dict) -> Taxonomy:
    where = f"[taxonomies.{name}]"
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must be a table.")
    _reject_unknown_keys(data, _TAXONOMY_KEYS, where)
    return Taxonomy(
        name=name,
        template=str(_require(data, "template", where)),
        permalink=str(_require(data, "permalink", where)),
        index_template=data.get("index_template"),
        index_permalink=data.get("index_permalink"),
    )


def _parse_home(data: dict) -> HomeConfig:
    where = "[home]"
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must be a table.")
    _reject_unknown_keys(data, _HOME_KEYS, where)
    recent = data.get("recent") or {}
    if recent and not isinstance(recent, dict):
        raise ConfigError(f"{where} 'recent' must be a table like {{ type = ..., count = ... }}.")
    _reject_unknown_keys(recent, _HOME_RECENT_KEYS, f"{where} 'recent'")
    return HomeConfig(
        template=str(_require(data, "template", where)),
        recent_type=recent.get("type"),
        recent_count=int(recent.get("count", 5)),
    )


def _parse_nav(data: dict) -> NavConfig:
    where = "[nav]"
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must be a table.")
    _reject_unknown_keys(data, _NAV_KEYS, where)
    labels = data.get("labels", [])
    links = data.get("links", [])
    if not isinstance(labels, list) or not isinstance(links, list):
        raise ConfigError(f"{where} 'labels' and 'links' must be arrays of strings.")
    if len(labels) != len(links):
        raise ConfigError(
            f"{where} 'labels' ({len(labels)}) and 'links' ({len(links)}) "
            "must have the same number of entries."
        )
    items = tuple(NavItem(label=str(label), link=str(link)) for label, link in zip(labels, links))
    return NavConfig(enabled=bool(data.get("enabled", True)), items=items)


def parse_config(raw: dict) -> SiteConfig:
    """Validate a raw config mapping into a :class:`SiteConfig`."""
    _reject_unknown_keys(raw, _TOP_LEVEL_KEYS, CONFIG_FILENAME)
    content_types = {
        name: _parse_content_type(name, data)
        for name, data in (raw.get("content_types") or {}).items()
    }
    taxonomies = {
        name: _parse_taxonomy(name, data)
        for name, data in (raw.get("taxonomies") or {}).items()
    }
    home = _parse_home(raw["home"]) if "home" in raw else None
    nav = _parse_nav(raw["nav"]) if "nav" in raw else NavConfig()

    # Cross-checks: taxonomy keys must not collide with reserved/front-matter
    # essentials, and the pages type (if present) must not declare an index.
    pages = content_types.get(PAGES_TYPE)
    if pages and pages.has_index:
        raise ConfigError(
            f"[content_types.{PAGES_TYPE}] is for standalone pages and must not "
            "declare 'index_template'/'index_permalink'."
        )

    return SiteConfig(
        title=str(raw.get("title", "Untitled Site")),
        base_url=str(raw.get("base_url", "")).rstrip("/"),
        home=home,
        nav=nav,
        content_types=content_types,
        taxonomies=taxonomies,
        raw=raw,
    )


def load_config(root: Path) -> SiteConfig:
    """Read and validate ``<root>/config.toml``."""
    path = root / CONFIG_FILENAME
    if not path.is_file():
        raise ConfigError(f"No {CONFIG_FILENAME} found in {root}.")
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {path}: {exc}") from exc
    return parse_config(raw)
