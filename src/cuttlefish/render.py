"""Render pages with Jinja2 and write them to ``public/``.

The renderer is deliberately strict about what listing templates can see: index,
taxonomy, taxonomy-index and home templates receive :class:`ContentSummary` views
(summary fields only), never full content bodies. Single-content and standalone
page templates receive the full :class:`ContentItem`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from jinja2 import (
    Environment,
    FileSystemLoader,
    StrictUndefined,
    TemplateSyntaxError,
    select_autoescape,
)

from cuttlefish.config import ContentType, SiteConfig
from cuttlefish.content import ContentItem, ContentSummary
from cuttlefish.errors import CuttlefishError
from cuttlefish.permalink import output_path
from cuttlefish.taxonomy import HomeTerm, TaxonomyData, Term, term_links

TEMPLATES_DIR = "templates"

#: Template-only pages that hosts serve for missing paths. They have no content
#: item and no pretty URL — the file lives at the site root as-is (its template
#: name is its output name, e.g. ``404.html`` -> ``public/404.html``), so they
#: sit outside the permalink/aggregate machinery. Ordered by convention.
ERROR_TEMPLATES = ("404.html",)


class RenderError(CuttlefishError):
    """Raised when a template fails to render."""

    default_summary = "Failed to render template"


def _jinja_detail(exc: Exception) -> str:
    """Turn a Jinja exception into a one-line reason with location where known."""
    if isinstance(exc, TemplateSyntaxError):
        where = exc.filename or exc.name or "template"
        return f"{where}:{exc.lineno}: {exc.message}"
    return f"{type(exc).__name__}: {exc}"


@contextmanager
def _render_step(target: str) -> Iterator[None]:
    """Wrap a render so any template error becomes a 'Failed to render <target>'."""
    try:
        yield
    except RenderError:
        raise
    except Exception as exc:
        raise RenderError(_jinja_detail(exc), summary=f"Failed to render {target}") from exc


#: A root-absolute URL inside an href/src attribute (but not a protocol-relative
#: "//host" URL, and not data-href etc. — the leading space anchors a real attr).
_ABS_URL_ATTR = re.compile(r'(\s(?:href|src)=")(/(?!/)[^"]*)')


def _prefix_links(html: str, base_path: str) -> str:
    """Prepend *base_path* to every root-absolute href/src in *html*.

    This is how subpath hosting works: links and assets are emitted root-absolute
    (``/blog/``, ``/css/main.css``), and here we rewrite them to ``/repo/blog/``
    etc. Doing it on the final HTML covers template links, nav, permalinks and
    author-written links in Markdown bodies in one place. Output *file* paths are
    untouched — only the URLs published in the HTML.
    """
    return _ABS_URL_ATTR.sub(lambda m: f"{m.group(1)}{base_path}{m.group(2)}", html)


@dataclass
class Page:
    """One page of a paginated listing."""

    items: list[ContentSummary]
    number: int
    total_pages: int
    base_url: str

    @property
    def has_prev(self) -> bool:
        return self.number > 1

    @property
    def has_next(self) -> bool:
        return self.number < self.total_pages

    @property
    def prev_url(self) -> str | None:
        if not self.has_prev:
            return None
        return self.base_url if self.number == 2 else f"{self.base_url}page/{self.number - 1}/"

    @property
    def next_url(self) -> str | None:
        if not self.has_next:
            return None
        return f"{self.base_url}page/{self.number + 1}/"


def _paginate(base_url: str, items: list, per_page: int) -> list[Page]:
    """Split *items* into pages. ``per_page <= 0`` means a single page."""
    if per_page <= 0 or len(items) <= per_page:
        return [Page(items=items, number=1, total_pages=1, base_url=base_url)]
    total = math.ceil(len(items) / per_page)
    pages = []
    for n in range(1, total + 1):
        chunk = items[(n - 1) * per_page : n * per_page]
        pages.append(Page(items=chunk, number=n, total_pages=total, base_url=base_url))
    return pages


def _page_url(base_url: str, number: int) -> str:
    return base_url if number == 1 else f"{base_url}page/{number}/"


class Renderer:
    """Renders templates against a site context and writes output files."""

    def __init__(self, root: Path, config: SiteConfig, public_dir: Path, base_path: str = ""):
        self.root = root
        self.config = config
        self.public_dir = public_dir
        self.base_path = base_path
        self.env = Environment(
            loader=FileSystemLoader(str(root / TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def set_site_context(self) -> None:
        """Expose a stable ``site`` global (title, base_url, nav, profile, params, config)."""
        self.env.globals["site"] = SimpleNamespace(
            title=self.config.title,
            base_url=self.config.base_url,
            nav=self.config.nav,
            profile=self.config.profile,
            params=self.config.params,
            config=self.config.raw,
        )

    # -- writing -----------------------------------------------------------

    def _write(self, output_rel: str, html: str) -> Path:
        if self.base_path:
            html = _prefix_links(html, self.base_path)
        dest = self.public_dir / output_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        return dest

    # -- page kinds --------------------------------------------------------

    def render_content(self, item: ContentItem) -> str:
        """Render a single content page (full body available)."""
        content_type = self.config.content_types[item.type]
        with _render_step(item.source_rel):
            html = self.env.get_template(content_type.template).render(
                page=item, item=item, type=item.type, terms=term_links(item, self.config)
            )
            self._write(item.output_rel, html)
        return item.output_rel

    def render_error_page(self, template_name: str) -> str:
        """Render a template-only error page (e.g. ``404.html``) to the site root.

        Error pages carry no content of their own and no pretty URL: hosts look
        for the file literally at the root (``public/404.html``), so we bypass
        the permalink mapping and render against the site-global context only
        (``site.*``). The output path is the template name unchanged.
        """
        with _render_step(template_name):
            html = self.env.get_template(template_name).render()
            self._write(template_name, html)
        return template_name

    def render_index(self, content_type: ContentType, items: list[ContentItem]) -> list[str]:
        """Render a content-type index (summary-only), paginated if configured."""
        if not content_type.has_index:
            return []
        base = content_type.index_permalink
        summaries = [i.summary for i in items]
        pages = _paginate(base, summaries, content_type.paginate)
        outputs = []
        for page in pages:
            url = _page_url(base, page.number)
            rel = self._output_rel(url)
            with _render_step(rel):
                html = self.env.get_template(content_type.index_template).render(
                    page=page, items=page.items, type=content_type.name
                )
                self._write(rel, html)
            outputs.append(rel)
        return outputs

    def render_term(self, data: TaxonomyData, term: Term) -> str:
        """Render one taxonomy term page (summary-only listing)."""
        summaries = [i.summary for i in term.items]
        with _render_step(term.output_rel):
            html = self.env.get_template(data.taxonomy.template).render(
                taxonomy=data.taxonomy.name,
                term=SimpleNamespace(name=term.name, url=term.url, count=term.count),
                items=summaries,
            )
            self._write(term.output_rel, html)
        return term.output_rel

    def render_taxonomy_index(self, data: TaxonomyData) -> str | None:
        """Render the index that lists every term of a taxonomy."""
        if not data.taxonomy.has_index or data.index_output_rel is None:
            return None
        terms = [SimpleNamespace(name=t.name, url=t.url, count=t.count) for t in data.sorted_terms]
        with _render_step(data.index_output_rel):
            html = self.env.get_template(data.taxonomy.index_template).render(
                taxonomy=data.taxonomy.name, terms=terms
            )
            self._write(data.index_output_rel, html)
        return data.index_output_rel

    def render_home(
        self,
        recent: dict[str, list[ContentItem]],
        taxonomies: dict[str, list[HomeTerm]] | None = None,
    ) -> str | None:
        """Render the landing page (recent items per type, summary-only).

        ``recent`` is exposed to the template as a mapping of content-type name
        to its summary items, so the template addresses sections by key
        (``recent.blog``) rather than being forced to loop over them.
        ``taxonomies`` maps a taxonomy name to its sorted terms (each with
        ``name``, ``count`` and ``url``), addressed as ``taxonomies.tags``.
        Author details are available via the site-wide ``site.profile`` global,
        not passed here.
        """
        home = self.config.home
        if home is None:
            return None
        sections = {name: [i.summary for i in items] for name, items in recent.items()}
        with _render_step("index.html"):
            html = self.env.get_template(home.template).render(
                recent=sections,
                taxonomies=taxonomies or {},
            )
            self._write("index.html", html)
        return "index.html"

    def index_output_rels(self, content_type: ContentType, count: int) -> list[str]:
        """Output paths a type index would produce, without rendering."""
        if not content_type.has_index:
            return []
        base = content_type.index_permalink
        pages = _paginate(base, list(range(count)), content_type.paginate)
        return [self._output_rel(_page_url(base, p.number)) for p in pages]

    # -- helpers -----------------------------------------------------------

    def _output_rel(self, url: str) -> str:
        return str(output_path(url, self.public_dir).relative_to(self.public_dir))
