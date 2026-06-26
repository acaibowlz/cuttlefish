"""Orchestrate a site build: discover, render, copy static, report.

Supports a full build and a hybrid incremental build (Milestone 1): unchanged
content pages are skipped; aggregates (indexes, taxonomy pages, home) are always
rebuilt; a change to a template invalidates the content pages that use it
(transitively); and a config change forces a full rebuild. Stale outputs left by
deletions/renames are pruned via the manifest.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from ass.cache import (
    Manifest,
    hash_file,
    hash_text,
    load_manifest,
    save_manifest,
)
from ass.config import CONFIG_FILENAME, ConfigError, SiteConfig, load_config
from ass.content import ContentItem, discover, sort_items
from ass.graph import AggregateSpec, aggregate_is_dirty, build_aggregate_specs
from ass.render import Renderer
from ass.taxonomy import build_taxonomies
from ass.template_deps import build_graph

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
    static: int = 0
    pruned: int = 0
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

    @property
    def counts_str(self) -> str:
        """Compact, zero-dropping breakdown of what this build produced."""
        if self.mode == "incremental":
            segs = [f"{self.content} changed", f"{self.skipped} unchanged"]
            if self.pruned:
                segs.append(f"{self.pruned} pruned")
            return ", ".join(segs)
        segs = [f"{self.content} pages"]
        indexes = self.indexes + self.taxonomy_indexes
        if indexes:
            segs.append(f"{indexes} indexes")
        if self.terms:
            segs.append(f"{self.terms} terms")
        if self.home:
            segs.append("home")
        if self.static:
            segs.append(f"{self.static} static")
        return ", ".join(segs)

    def summary_line(self, title: str) -> str:
        """One-line glyph summary printed after a build."""
        verb = "Rebuilt" if self.mode == "incremental" else "Built"
        return (
            f"[green]✓[/green] {verb} [bold]{title}[/bold] in {self.elapsed_str} "
            f"[dim]·[/dim] {self.counts_str}"
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
        if group and ct.sort_by != "date" and not any(ct.sort_by in item.meta for item in group):
            raise ConfigError(
                f"[content_types.{name}] 'sort_by' = {ct.sort_by!r} is not a field on any "
                f"{name} content. Use \"date\" or a front-matter field present on your items."
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
    console: Console | None = None,
) -> BuildStats:
    console = console or Console()
    start = time.perf_counter()
    root = root.resolve()
    config = load_config(root)
    public_dir = root / PUBLIC_DIR
    config_hash = hash_text((root / CONFIG_FILENAME).read_text(encoding="utf-8"))

    manifest = None if force else load_manifest(root)
    incremental = (
        manifest is not None
        and public_dir.exists()
        and manifest.config_hash == config_hash
    )

    items = discover(root, config, drafts=drafts)
    grouped = _items_by_type(items, config)
    taxonomies = build_taxonomies(items, config)

    renderer = Renderer(root, config, public_dir)
    renderer.set_site_context()
    graph = build_graph(root, renderer.env)

    if incremental:
        stats = _incremental_build(
            root, config, config_hash, public_dir, items, grouped,
            taxonomies, renderer, graph, manifest,
        )
    else:
        stats = _full_build(
            root, config, config_hash, public_dir, items, grouped,
            taxonomies, renderer, graph,
        )

    stats.elapsed_ms = (time.perf_counter() - start) * 1000
    console.print(stats.summary_line(config.title))
    return stats


def _full_build(root, config, config_hash, public_dir, items, grouped, taxonomies, renderer, graph) -> BuildStats:
    stats = BuildStats(mode="full")
    if public_dir.exists():
        shutil.rmtree(public_dir)
    public_dir.mkdir(parents=True)

    new_content: dict[str, dict] = {}
    for item in items:
        renderer.render_content(item)
        stats.content += 1
        src = root / item.source_rel
        new_content[item.source_rel] = {
            "hash": hash_file(src),
            "outputs": [item.output_rel],
        }

    specs = build_aggregate_specs(config, grouped, taxonomies, renderer)
    for spec in specs:
        spec.render()
        stats.count_rendered(spec.key)

    new_static: dict[str, dict] = {}
    for src_rel, out_rel in _static_files(root).items():
        src = root / src_rel
        dest = public_dir / out_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        new_static[src_rel] = {"hash": hash_file(src), "output": out_rel}
        stats.static += 1

    save_manifest(root, Manifest(
        config_hash=config_hash,
        content=new_content,
        templates=_template_manifest(root, graph),
        static=new_static,
        aggregates=_aggregates_manifest(specs),
    ))
    return stats


def _incremental_build(root, config, config_hash, public_dir, items, grouped, taxonomies, renderer, graph, manifest) -> BuildStats:
    stats = BuildStats(mode="incremental")

    # Which templates changed, and which templates are therefore affected?
    new_templates = _template_manifest(root, graph)
    changed_templates = {
        name for name, entry in new_templates.items()
        if manifest.templates.get(name, {}).get("hash") != entry["hash"]
    }
    affected_templates = graph.affected_by(changed_templates)

    # A content type is "template-dirty" if its single template is affected.
    type_dirty = {
        name: ct.template in affected_templates
        for name, ct in config.content_types.items()
    }

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
    specs = build_aggregate_specs(config, grouped, taxonomies, renderer)
    for spec in specs:
        if aggregate_is_dirty(spec, manifest.aggregates, affected_templates):
            spec.render()
            stats.count_rendered(spec.key)
        else:
            stats.aggregates_skipped += 1

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
    )

    # Prune outputs that existed last time but are no longer produced
    # (deleted content, renamed slugs, removed terms, removed static files).
    stats.pruned = _prune(public_dir, manifest.all_outputs(), new_manifest.all_outputs())

    save_manifest(root, new_manifest)
    return stats


def _prune(public_dir: Path, old_outputs: set[str], new_outputs: set[str]) -> int:
    """Delete output files present last build but not this one."""
    pruned = 0
    for rel in old_outputs - new_outputs:
        target = public_dir / rel
        if target.is_file():
            target.unlink()
            pruned += 1
            # Clean up now-empty parent directories.
            parent = target.parent
            while parent != public_dir and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent
    return pruned
