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
from urllib.parse import urlsplit

from cuttlefish.errors import CuttlefishError

#: The content type name reserved for standalone pages (no index, no taxonomy).
PAGES_TYPE = "pages"

CONFIG_FILENAME = "config.toml"

#: Where config errors point users for the full key reference.
CONFIG_DOCS_URL = "https://acaibowlz.github.io/cuttlefish/configuration/"

#: Allowed keys for each strictly-validated config scope. Unknown keys are
#: rejected — they are almost always typos that would otherwise be silently
#: ignored. The one escape hatch is the ``[params]`` table, whose *contents*
#: are deliberately free-form (see ``_parse_params``); custom site-wide values
#: go there rather than as loose top-level keys.
_TOP_LEVEL_KEYS = frozenset(
    {"title", "base_url", "content_types", "taxonomies", "home", "nav", "profile", "params"}
)
_PROFILE_KEYS = frozenset({"name", "bio", "avatar", "email", "socials"})
_CONTENT_TYPE_KEYS = frozenset(
    {"template", "permalink", "index_template", "index_permalink", "paginate", "sort_by", "order"}
)
_TAXONOMY_KEYS = frozenset(
    {
        "template",
        "permalink",
        "index_template",
        "index_permalink",
        "multiple",
        "sort_by",
        "order",
        "home",
        "items",
    }
)
#: Keys allowed in the nested ``[taxonomies.<name>.items]`` sub-table, which sets
#: how *items* are ordered on a term page (distinct from the term ordering above).
_TAXONOMY_ITEMS_KEYS = frozenset({"sort_by", "order"})
_HOME_KEYS = frozenset({"template", "recent"})
_NAV_KEYS = frozenset({"enabled", "labels", "links"})


class ConfigError(CuttlefishError):
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
    #: Term cardinality expected in front matter. ``True`` requires a list of
    #: terms (e.g. ``tags = ["travel", "japan"]``); ``False`` requires a single
    #: string term (e.g. ``category = "AI"``). Enforced when parsing content.
    multiple: bool = True
    #: How this taxonomy's terms are ordered wherever they are listed (the term
    #: index page and, if surfaced, the home list): ``"name"`` (the term text) or
    #: ``"count"`` (most-used first), each ``"asc"``/``"desc"``.
    sort_by: str = "name"
    order: str = "asc"
    #: How *items* are ordered on a term page — a separate axis from the term
    #: ordering above, set under ``[taxonomies.<name>.items]``. Open-ended like a
    #: content type's ``sort_by`` (any front-matter field, validated against real
    #: items at build time); defaults to newest-first, matching a type index.
    item_sort_by: str = "date"
    item_order: str = "desc"
    #: Surface this taxonomy's terms on the landing page. When ``True`` the home
    #: template receives its terms as ``taxonomies.<name>`` (each with ``name``,
    #: ``count`` and ``url``), ordered by ``sort_by``/``order`` above.
    home: bool = False

    @property
    def descending(self) -> bool:
        return self.order == "desc"

    @property
    def has_index(self) -> bool:
        return self.index_template is not None and self.index_permalink is not None


@dataclass(frozen=True)
class HomeConfig:
    """The landing page configuration."""

    template: str
    #: Landing-page sections: content-type name -> number of recent items to
    #: pass to the template (exposed as ``recent.<type>``).
    recent: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Profile:
    """Site author/owner details, exposed to every template as ``site.profile``.

    ``socials`` maps a platform key (e.g. ``github``) to its URL; keys keep
    config order, so links render in the order they are written and the key is
    available to templates for icon/label lookup.
    """

    name: str = ""
    bio: str = ""
    avatar: str = ""  # path under static/, e.g. "/img/avatar.png"
    email: str = ""
    socials: dict[str, str] = field(default_factory=dict)


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
    profile: Profile | None = None
    content_types: dict[str, ContentType] = field(default_factory=dict)
    taxonomies: dict[str, Taxonomy] = field(default_factory=dict)
    #: Free-form ``[params]`` table, exposed to every template as ``site.params``.
    #: Its keys are intentionally not validated — this is the escape hatch for
    #: custom site-wide values a template wants to read.
    params: dict = field(default_factory=dict)
    #: URL path prefix the site is served under, derived from ``base_url`` (e.g.
    #: ``/repo`` for a GitHub Pages project site). Empty for a root deploy.
    base_path: str = ""
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
        raise ConfigError(f'{where} \'order\' must be "asc" or "desc", got {order!r}.')
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
    multiple = data.get("multiple", True)
    if not isinstance(multiple, bool):
        raise ConfigError(f"{where} 'multiple' must be a boolean, got {multiple!r}.")
    sort_by = str(data.get("sort_by", "name")).lower()
    if sort_by not in ("count", "name"):
        raise ConfigError(f'{where} \'sort_by\' must be "count" or "name", got {sort_by!r}.')
    order = str(data.get("order", "asc")).lower()
    if order not in ("asc", "desc"):
        raise ConfigError(f'{where} \'order\' must be "asc" or "desc", got {order!r}.')
    home = data.get("home", False)
    if not isinstance(home, bool):
        raise ConfigError(f"{where} 'home' must be a boolean, got {home!r}.")
    item_sort_by, item_order = _parse_item_sort(data.get("items", {}), f"{where}.items")
    return Taxonomy(
        name=name,
        template=str(_require(data, "template", where)),
        permalink=str(_require(data, "permalink", where)),
        index_template=data.get("index_template"),
        index_permalink=data.get("index_permalink"),
        multiple=multiple,
        sort_by=sort_by,
        order=order,
        item_sort_by=item_sort_by,
        item_order=item_order,
        home=home,
    )


def _parse_item_sort(data: dict, where: str) -> tuple[str, str]:
    """Parse a ``[taxonomies.<name>.items]`` sub-table into ``(sort_by, order)``.

    ``sort_by`` is a front-matter field name — open-ended like a content type's,
    so it is *not* checked against a closed set here (a field present on no item
    is flagged at build time, where the items are known). ``order`` is validated.
    """
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must be a table.")
    _reject_unknown_keys(data, _TAXONOMY_ITEMS_KEYS, where)
    sort_by = str(data.get("sort_by", "date"))
    order = str(data.get("order", "desc")).lower()
    if order not in ("asc", "desc"):
        raise ConfigError(f'{where} \'order\' must be "asc" or "desc", got {order!r}.')
    return sort_by, order


def _parse_home(data: dict) -> HomeConfig:
    where = "[home]"
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must be a table.")
    _reject_unknown_keys(data, _HOME_KEYS, where)
    recent = _parse_count_table(data, "recent", where)
    return HomeConfig(
        template=str(_require(data, "template", where)),
        recent=recent,
    )


def _parse_count_table(data: dict, key: str, where: str) -> dict[str, int]:
    """Parse a ``content-type = count`` table (e.g. recent); count >= 0."""
    raw = data.get(key) or {}
    if not isinstance(raw, dict):
        raise ConfigError(
            f"{where} '{key}' must be a table of content-type = count, "
            "e.g. {{ blog = 5, project = 3 }}."
        )
    result: dict[str, int] = {}
    for type_name, count in raw.items():
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ConfigError(
                f"{where} '{key}.{type_name}' must be a non-negative integer, got {count!r}."
            )
        result[type_name] = count
    return result


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
    items = tuple(
        NavItem(label=str(label), link=str(link))
        for label, link in zip(labels, links, strict=True)  # lengths checked above
    )
    return NavConfig(enabled=bool(data.get("enabled", True)), items=items)


def _parse_profile(data: dict) -> Profile:
    where = "[profile]"
    if not isinstance(data, dict):
        raise ConfigError(f"{where} must be a table.")
    _reject_unknown_keys(data, _PROFILE_KEYS, where)
    raw_socials = data.get("socials") or {}
    if not isinstance(raw_socials, dict):
        raise ConfigError(
            f"{where} 'socials' must be a table of platform = url, "
            'e.g. {{ github = "https://github.com/you" }}.'
        )
    socials = {str(key): str(url) for key, url in raw_socials.items()}
    return Profile(
        name=str(data.get("name", "")),
        bio=str(data.get("bio", "")),
        avatar=str(data.get("avatar", "")),
        email=str(data.get("email", "")),
        socials=socials,
    )


def _parse_params(data: dict) -> dict:
    """Return the free-form ``[params]`` table verbatim.

    Unlike every other scope, its keys are *not* checked: this is the one place
    a site can declare custom values for its templates to read. We only enforce
    that it is a table, so ``site.params.foo`` lookups behave predictably.
    """
    if not isinstance(data, dict):
        raise ConfigError("[params] must be a table of custom key = value entries.")
    return data


def parse_config(raw: dict) -> SiteConfig:
    """Validate a raw config mapping into a :class:`SiteConfig`."""
    _reject_unknown_keys(raw, _TOP_LEVEL_KEYS, CONFIG_FILENAME)
    content_types = {
        name: _parse_content_type(name, data)
        for name, data in (raw.get("content_types") or {}).items()
    }
    taxonomies = {
        name: _parse_taxonomy(name, data) for name, data in (raw.get("taxonomies") or {}).items()
    }
    home = _parse_home(raw["home"]) if "home" in raw else None
    nav = _parse_nav(raw["nav"]) if "nav" in raw else NavConfig()
    profile = _parse_profile(raw["profile"]) if "profile" in raw else None
    params = _parse_params(raw["params"]) if "params" in raw else {}

    # Cross-checks: taxonomy keys must not collide with reserved/front-matter
    # essentials, and the pages type (if present) must not declare an index.
    pages = content_types.get(PAGES_TYPE)
    if pages and pages.has_index:
        raise ConfigError(
            f"[content_types.{PAGES_TYPE}] is for standalone pages and must not "
            "declare 'index_template'/'index_permalink'."
        )
    if home is not None:
        for type_name in home.recent:
            if type_name not in content_types:
                raise ConfigError(f"[home] 'recent' references unknown content type {type_name!r}.")

    base_url = str(raw.get("base_url", "")).rstrip("/")
    return SiteConfig(
        title=str(raw.get("title", "Untitled Site")),
        base_url=base_url,
        # base_url's path component is the subpath the site is served under;
        # internal links get prefixed with it so subpath hosting works.
        base_path=urlsplit(base_url).path.rstrip("/"),
        home=home,
        nav=nav,
        profile=profile,
        content_types=content_types,
        taxonomies=taxonomies,
        params=params,
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
