"""Orchestrate a site build: discover, render, copy static, report.

There is one build path (``_run_build``) that renders whatever differs from a
given manifest: unchanged content pages are skipped; an aggregate (index,
taxonomy page, home) rebuilds when its fingerprint or template changed; a
changed template invalidates the pages that use it (transitively); and stale
outputs from deletions/renames are pruned via the manifest. A *full* build is
the same routine run against an empty manifest on a cleared ``public/`` (so
everything is "changed"); an *incremental* build passes the previous manifest.
A config change forces the full variant. Keeping one path means full and
incremental cannot disagree by construction.
"""

from __future__ import annotations

import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from cuttlefish.cache import (
    Manifest,
    hash_file,
    hash_text,
    load_manifest,
    save_manifest,
)
from cuttlefish.config import CONFIG_FILENAME, ConfigError, SiteConfig, load_config
from cuttlefish.content import ContentError, ContentItem, discover, sort_items
from cuttlefish.graph import (
    AggregateSpec,
    aggregate_is_dirty,
    build_aggregate_specs,
    build_feed_specs,
)
from cuttlefish.render import ERROR_TEMPLATES, Renderer
from cuttlefish.robots import ROBOTS_FILENAME, write_robots
from cuttlefish.sitemap import write_sitemap
from cuttlefish.taxonomy import build_taxonomies
from cuttlefish.template_deps import build_graph

PUBLIC_DIR = "public"
STATIC_DIR = "static"


@dataclass
class BuildStats:
    content: int = 0
    skipped: int = 0
    indexes: int = 0
    terms: int = 0
    taxonomy_indexes: int = 0
    home: int = 0
    aggregates_skipped: int = 0
    error_pages: int = 0
    static: int = 0
    pruned: int = 0
    feeds: int = 0
    feeds_skipped: int = 0
    sitemap: bool = False
    robots: bool = False
    mode: str = "full"
    elapsed_ms: float = 0.0

    def count_rendered(self, key: str) -> None:
        if key.startswith("index:"):
            self.indexes += 1
        elif key.startswith("taxonomy_index:"):
            self.taxonomy_indexes += 1
        elif key.startswith("taxonomy:"):
            self.terms += 1
        elif key == "home":
            self.home = 1

    @property
    def elapsed_str(self) -> str:
        """Human-friendly build duration (``45ms`` / ``1.20s``)."""
        if self.elapsed_ms < 1000:
            return f"{self.elapsed_ms:.0f}ms"
        return f"{self.elapsed_ms / 1000:.2f}s"

    def detail_lines(self, *, outputs: bool = True) -> list[str]:
        """One line per kind of output this build produced; untouched kinds are omitted.

        Counts read "1 of 4 content pages" when some were skipped as unchanged,
        so full and incremental builds share one vocabulary. *outputs* = False
        drops the file-level lines (copies, removals, sitemap) for ``check``,
        which writes nothing.
        """
        listings = self.indexes + self.taxonomy_indexes + self.terms + self.home
        # sitemap.xml and robots.txt are rewritten on every build, so they are
        # only worth reporting on a full one.
        full = outputs and self.mode == "full"
        lines = [
            _done_of(self.content, self.content + self.skipped, "content page"),
            _done_of(listings, listings + self.aggregates_skipped, "listing page"),
            f"{_plural(self.static, 'static file')} copied" if outputs and self.static else "",
            "RSS feed" if self.feeds else "",
            "404.html" if self.error_pages else "",
            "sitemap.xml" if full and self.sitemap else "",
            "robots.txt" if full and self.robots else "",
            f"{_plural(self.pruned, 'stale file')} removed" if outputs and self.pruned else "",
        ]
        return [line for line in lines if line]

    def report(self, headline: str, *, outputs: bool = True) -> str:
        """*headline* followed by an indented line per kind of output."""
        return "\n".join([headline, *(f"  {line}" for line in self.detail_lines(outputs=outputs))])

    def summary(self, title: str) -> str:
        """Multi-line summary printed after a build."""
        if self.mode == "incremental" and not self.detail_lines():
            return f"[green]✓[/green] [bold]{title}[/bold] is up to date [dim]({self.elapsed_str})[/dim]"
        verb = "Rebuilt" if self.mode == "incremental" else "Built"
        return self.report(f"[green]✓[/green] {verb} [bold]{title}[/bold] in {self.elapsed_str}")


def _plural(n: int, noun: str) -> str:
    return f"[bold cyan]{n}[/bold cyan] {noun}{'' if n == 1 else 's'}"


def _done_of(done: int, total: int, noun: str) -> str:
    """``4 content pages``, or ``1 of 4 content pages`` when some were skipped."""
    if not done:
        return ""
    return (
        _plural(done, noun)
        if done == total
        else f"[bold cyan]{done}[/bold cyan] of {_plural(total, noun)}"
    )


# -- shared helpers --------------------------------------------------------


def _items_by_type(items: list[ContentItem], config: SiteConfig) -> dict[str, list[ContentItem]]:
    grouped: dict[str, list[ContentItem]] = {name: [] for name in config.content_types}
    for item in items:
        grouped.setdefault(item.type, []).append(item)
    for name, group in grouped.items():
        ct = config.content_types[name]
        # 'sort_by' is open-ended (any front-matter field), so it can't be
        # validated against a closed set at config-parse time the way 'order'
        # is. Here we have the items, so a key that appears on *none* of them is
        # almost certainly a typo (e.g. "dae" for "date") rather than a real but
        # absent field — surface it instead of silently leaving them unsorted.
        # Empty types are skipped: "absent everywhere" is vacuously true there.
        if (
            group
            and ct.sort_by != "date"
            and not any(item.has_sort_field(ct.sort_by) for item in group)
        ):
            raise ConfigError(
                f"[content_types.{name}] 'sort_by' = {ct.sort_by!r} is not a field on any "
                f'{name} content. Use "date" or a front-matter field present on your items.'
            )
        grouped[name] = sort_items(group, sort_by=ct.sort_by, order=ct.order)
    return grouped


def _static_files(root: Path) -> dict[str, str]:
    """Map static source paths (rel to root) -> output paths (rel to public)."""
    static_root = root / STATIC_DIR
    mapping: dict[str, str] = {}
    if not static_root.is_dir():
        return mapping
    for src in static_root.rglob("*"):
        if src.is_file():
            src_rel = str(src.relative_to(root)).replace("\\", "/")
            out_rel = str(src.relative_to(static_root)).replace("\\", "/")
            mapping[src_rel] = out_rel
    return mapping


def _describe_spec(spec: AggregateSpec) -> str:
    """Name an aggregate the way the user configured it (``index:blog`` -> the blog index)."""
    kind, _, rest = spec.key.partition(":")
    if kind == "index":
        return f"the {rest} index"
    if kind == "taxonomy":
        taxonomy, _, term = rest.partition(":")
        return f"the {taxonomy} term page for {term!r}"
    if kind == "taxonomy_index":
        return f"the {rest} index"
    return f"the {kind} page" if kind == "home" else f"the {kind}"


def _check_unique_outputs(outputs: list[tuple[str, str]]) -> None:
    """Refuse two sources writing one file: the later would silently overwrite the earlier.

    Runs before anything is written, over every kind of output (content,
    listings, the feed, error pages, static files), so e.g. a page with
    ``slug = "blog"`` colliding with the blog index is caught too.
    """
    seen: dict[str, str] = {}
    for output, source in outputs:
        if output in seen:
            raise ContentError(
                f"{seen[output]} and {source} both produce /{output}. "
                "Rename one so they map to different URLs.",
                summary="Duplicate output",
            )
        seen[output] = source


def _aggregates_manifest(specs: list[AggregateSpec]) -> dict[str, dict]:
    return {
        spec.key: {
            "fingerprint": spec.fingerprint,
            "template": spec.template,
            "outputs": spec.outputs,
        }
        for spec in specs
    }


def _template_manifest(root: Path, env_graph) -> dict[str, dict]:
    tdir = root / "templates"
    result: dict[str, dict] = {}
    for name, refs in env_graph.refs.items():
        path = tdir / name
        result[name] = {"hash": hash_file(path), "refs": sorted(refs)}
    return result


# -- entry point -----------------------------------------------------------


def build_site(
    root: Path,
    *,
    force: bool = False,
    drafts: bool = False,
    base_path: str | None = None,
    console: Console | None = None,
    output_dir: Path | None = None,
    persist: bool = True,
) -> BuildStats:
    console = console or Console()
    start = time.perf_counter()
    root = root.resolve()
    config = load_config(root)
    # public_dir is where output is written; ``check`` points it at a throwaway
    # temp dir and sets persist=False so nothing in the site is touched.
    public_dir = (root / PUBLIC_DIR) if output_dir is None else output_dir

    # base_path defaults to the one derived from base_url, but callers (the dev
    # server) can force "" to preview at the local root without the prefix. It
    # changes every emitted link, so it is part of config_hash: switching it
    # (e.g. between `ctf build` and `ctf serve`) must invalidate the incremental
    # cache, or unchanged pages would keep the previous build's prefix.
    effective_base_path = config.base_path if base_path is None else base_path
    config_hash = hash_text(
        (root / CONFIG_FILENAME).read_text(encoding="utf-8") + f"\nbase_path={effective_base_path}"
    )

    manifest = None if force else load_manifest(root)
    incremental = (
        manifest is not None and public_dir.exists() and manifest.config_hash == config_hash
    )

    items = discover(root, config, drafts=drafts)
    grouped = _items_by_type(items, config)
    taxonomies = build_taxonomies(items, config)

    renderer = Renderer(root, config, public_dir, base_path=effective_base_path)
    renderer.set_site_context()
    graph = build_graph(root, renderer.env)

    if incremental:
        stats, new_manifest = _run_build(
            root,
            config,
            config_hash,
            public_dir,
            items,
            grouped,
            taxonomies,
            renderer,
            graph,
            manifest,
            mode="incremental",
        )
    else:
        # A full build is just the incremental routine against an *empty*
        # manifest: nothing matches, so every page/aggregate/static file is
        # "dirty" and rebuilt. We only clear public/ first (there is no manifest
        # to prune stale files against) and then run the one shared path — so
        # full and incremental cannot drift out of agreement by construction.
        if public_dir.exists():
            shutil.rmtree(public_dir)
        public_dir.mkdir(parents=True)
        stats, new_manifest = _run_build(
            root,
            config,
            config_hash,
            public_dir,
            items,
            grouped,
            taxonomies,
            renderer,
            graph,
            Manifest(),
            mode="full",
        )

    # Persist the incremental cache unless the caller opted out (``check``).
    if persist:
        save_manifest(root, new_manifest)

    stats.elapsed_ms = (time.perf_counter() - start) * 1000
    # highlight=False: Rich's auto-highlighter would recolor whatever looks like a
    # number or Python literal (a title like "True North", a "404" label).
    console.print(stats.summary(config.title), highlight=False)
    return stats


def check_site(root: Path, *, drafts: bool = False, console: Console | None = None) -> BuildStats:
    """Validate the site without writing it — the same pipeline as ``build``.

    Runs a full build so config, content, permalinks and *every template* are
    exercised: any error a real ``ctf build`` would raise surfaces here. But the
    output goes to a throwaway temporary directory and the incremental cache
    (``.ctf/``) is not touched (``persist=False``), so nothing in the site is
    created or changed. Reusing ``build_site`` keeps this on the one build path —
    ``check`` cannot pass while ``build`` fails.
    """
    console = console or Console()
    root = root.resolve()
    config = load_config(root)  # fail fast on config errors; also gives the title
    with tempfile.TemporaryDirectory(prefix="ctf-check-") as tmp:
        stats = build_site(
            root,
            force=True,
            drafts=drafts,
            console=Console(quiet=True),
            output_dir=Path(tmp) / PUBLIC_DIR,
            persist=False,
        )
    console.print(
        stats.report(
            f"[green]✓[/green] Checked [bold]{config.title}[/bold] in {stats.elapsed_str} "
            "[dim](nothing written)[/dim]",
            outputs=False,
        ),
        highlight=False,
    )
    return stats


def _run_build(
    root,
    config,
    config_hash,
    public_dir,
    items,
    grouped,
    taxonomies,
    renderer,
    graph,
    manifest,
    *,
    mode,
) -> tuple[BuildStats, Manifest]:
    """Render the site by diffing against *manifest*; return stats + the new manifest.

    This is the single build path. An incremental build passes the previous
    manifest; a full build passes an empty :class:`Manifest` (and pre-clears
    ``public/``), which makes every unit of work register as changed. Because
    both modes run this exact routine, they are guaranteed to produce identical
    output for identical inputs — there is no second implementation to drift.

    Persisting the returned manifest is the caller's choice (``build`` saves it;
    ``check`` discards it), so this routine has no cache side effect of its own.
    """
    stats = BuildStats(mode=mode)

    # Which templates changed, and which templates are therefore affected?
    new_templates = _template_manifest(root, graph)
    changed_templates = {
        name
        for name, entry in new_templates.items()
        if manifest.templates.get(name, {}).get("hash") != entry["hash"]
    }
    affected_templates = graph.affected_by(changed_templates)

    # A content type is "template-dirty" if its single template is affected.
    type_dirty = {
        name: ct.template in affected_templates for name, ct in config.content_types.items()
    }

    specs = build_aggregate_specs(config, grouped, taxonomies, renderer)
    feed_specs = build_feed_specs(config, grouped, renderer)
    _check_unique_outputs(
        [(i.output_rel, i.source_rel) for i in items]
        + [(out, _describe_spec(s)) for s in specs + feed_specs for out in s.outputs]
        + [(name, f"templates/{name}") for name in ERROR_TEMPLATES if name in new_templates]
        + [(out, src) for src, out in _static_files(root).items()]
    )

    # Content pages: render only those that changed or use a dirty template.
    new_content: dict[str, dict] = {}
    for item in items:
        src = root / item.source_rel
        file_hash = hash_file(src)
        old = manifest.content.get(item.source_rel)
        outputs = [item.output_rel]
        needs_build = (
            old is None
            or old.get("hash") != file_hash
            or type_dirty.get(item.type, False)
            or old.get("outputs") != outputs
        )
        if needs_build:
            renderer.render_content(item)
            stats.content += 1
        else:
            stats.skipped += 1
        new_content[item.source_rel] = {"hash": file_hash, "outputs": outputs}

    # Aggregates: rebuild only those whose fingerprint changed or whose
    # template was (transitively) affected (Milestone 2 dependency graph).
    for spec in specs:
        if aggregate_is_dirty(spec, manifest.aggregates, affected_templates):
            spec.render()
            stats.count_rendered(spec.key)
        else:
            stats.aggregates_skipped += 1

    # Error pages: template-only pages (e.g. 404.html) that hosts serve for
    # missing paths. They have no content source and no pretty URL — the file
    # lives at the site root as-is — so they sit outside the aggregate/permalink
    # machinery. Present only when the author added the template. Rebuild when
    # that template (transitively) changed or is newly added; prune via the
    # manifest when it is removed. A full build passes an empty manifest, so
    # every present error page counts as new and is rendered.
    new_error_pages: dict[str, dict] = {}
    for template_name in ERROR_TEMPLATES:
        if template_name not in new_templates:
            continue  # author hasn't added this error template
        old = manifest.error_pages.get(template_name)
        if old is None or template_name in affected_templates or old.get("output") != template_name:
            renderer.render_error_page(template_name)
            stats.error_pages += 1
        new_error_pages[template_name] = {"output": template_name}

    # RSS feed: one site-wide summary aggregate over the types with feed = true,
    # rebuilt only when its listed items' metadata changed. Tracked in
    # their own manifest section so they are pruned but never enter the sitemap —
    # the same treatment as error pages. Absent entirely unless base_url is set.
    new_feeds: dict[str, dict] = {}
    for spec in feed_specs:
        if aggregate_is_dirty(spec, manifest.feeds, affected_templates):
            spec.render()
            stats.feeds += 1
        else:
            stats.feeds_skipped += 1
        new_feeds[spec.key] = {
            "fingerprint": spec.fingerprint,
            "template": spec.template,
            "outputs": spec.outputs,
        }

    # Static: copy new/changed files; track for pruning.
    new_static: dict[str, dict] = {}
    for src_rel, out_rel in _static_files(root).items():
        src = root / src_rel
        file_hash = hash_file(src)
        old = manifest.static.get(src_rel)
        if old is None or old.get("hash") != file_hash or old.get("output") != out_rel:
            dest = public_dir / out_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            stats.static += 1
        new_static[src_rel] = {"hash": file_hash, "output": out_rel}

    new_manifest = Manifest(
        config_hash=config_hash,
        content=new_content,
        templates=new_templates,
        static=new_static,
        aggregates=_aggregates_manifest(specs),
        error_pages=new_error_pages,
        feeds=new_feeds,
    )

    # Prune outputs that existed last time but are no longer produced
    # (deleted content, renamed slugs, removed terms, removed static files).
    stats.pruned = _prune(public_dir, manifest.all_outputs(), new_manifest.all_outputs())

    # Every build parses every item, so <lastmod> is always current even when
    # the page itself was skipped as unchanged.
    lastmod = {i.output_rel: i.updated or i.date for i in items if i.updated or i.date}
    stats.sitemap = write_sitemap(public_dir, new_manifest.page_outputs(), config.base_url, lastmod)
    # robots.txt: generated unless the site ships its own static/robots.txt, in
    # which case the verbatim static copy already produced public/robots.txt and
    # we leave it alone.
    robots_overridden = (root / STATIC_DIR / ROBOTS_FILENAME).is_file()
    stats.robots = write_robots(public_dir, config.base_url, user_provided=robots_overridden)
    return stats, new_manifest


def _prune(public_dir: Path, old_outputs: set[str], new_outputs: set[str]) -> int:
    """Delete output files present last build but not this one."""
    pruned = 0
    root = public_dir.resolve()
    for rel in old_outputs - new_outputs:
        target = public_dir / rel
        # The manifest is a file on disk: never let an entry delete (or walk the
        # empty-directory cleanup) outside public/.
        if not target.resolve().is_relative_to(root):
            continue
        if target.is_file():
            target.unlink()
            pruned += 1
            # Clean up now-empty parent directories.
            parent = target.parent
            while parent != public_dir and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    return pruned
