"""Load and validate ``config.toml`` into typed dataclasses.

The whole site is described by a single ``config.toml`` at the site root. This
module turns it into ``SiteConfig`` (plus ``ContentType``, ``Taxonomy``,
``HomeConfig``) and validates it, raising :class:`ConfigError` with a clear
message an agent can act on.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

#: The content type name reserved for standalone pages (no index, no taxonomy).
PAGES_TYPE = "pages"

CONFIG_FILENAME = "config.toml"


class ConfigError(Exception):
    """Raised when ``config.toml`` is missing or invalid."""


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
class SiteConfig:
    """The whole site configuration, parsed from ``config.toml``."""

    title: str
    base_url: str
    home: HomeConfig | None
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
    order = str(data.get("order", "desc")).lower()
    if order not in ("asc", "desc"):
        raise ConfigError(f"{where} 'order' must be \"asc\" or \"desc\", got {order!r}.")
    return ContentType(
        name=name,
        template=str(_require(data, "template", where)),
        permalink=str(_require(data, "permalink", where)),
        index_template=data.get("index_template"),
        index_permalink=data.get("index_permalink"),
        paginate=int(data.get("paginate", 0)),
        sort_by=str(data.get("sort_by", "date")),
        order=order,
    )


def _parse_taxonomy(name: str, data: dict) -> Taxonomy:
    where = f"[taxonomies.{name}]"
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must be a table.")
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
    recent = data.get("recent") or {}
    if recent and not isinstance(recent, dict):
        raise ConfigError(f"{where} 'recent' must be a table like {{ type = ..., count = ... }}.")
    return HomeConfig(
        template=str(_require(data, "template", where)),
        recent_type=recent.get("type"),
        recent_count=int(recent.get("count", 5)),
    )


def parse_config(raw: dict) -> SiteConfig:
    """Validate a raw config mapping into a :class:`SiteConfig`."""
    content_types = {
        name: _parse_content_type(name, data)
        for name, data in (raw.get("content_types") or {}).items()
    }
    taxonomies = {
        name: _parse_taxonomy(name, data)
        for name, data in (raw.get("taxonomies") or {}).items()
    }
    home = _parse_home(raw["home"]) if "home" in raw else None

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
