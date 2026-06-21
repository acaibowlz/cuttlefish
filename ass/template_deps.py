"""Track Jinja2 template-to-template dependencies.

A template that ``{% extends %}`` or ``{% include %}`` another depends on it, so
a change to a base/partial must invalidate everything that (transitively) uses
it. We parse each template's direct references and expose transitive closures in
both directions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, meta

TEMPLATES_DIR = "templates"


@dataclass
class TemplateGraph:
    """Forward (``depends_on``) and reverse (``used_by``) template edges."""

    #: template name -> set of template names it directly references
    refs: dict[str, set[str]] = field(default_factory=dict)

    def direct_refs(self, name: str) -> set[str]:
        return self.refs.get(name, set())

    def closure(self, name: str) -> set[str]:
        """All templates *name* transitively depends on (including itself)."""
        seen: set[str] = set()
        stack = [name]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self.refs.get(current, set()))
        return seen

    def affected_by(self, changed: set[str]) -> set[str]:
        """All templates whose render output depends on any *changed* template.

        Reverse reachability: returns every template T such that
        ``closure(T)`` intersects *changed* (includes the changed ones).
        """
        result: set[str] = set()
        for name in self.refs:
            if self.closure(name) & changed:
                result.add(name)
        result |= changed
        return result


def _list_templates(root: Path) -> list[Path]:
    tdir = root / TEMPLATES_DIR
    if not tdir.is_dir():
        return []
    return [p for p in tdir.rglob("*.html") if p.is_file()]


def build_graph(root: Path, env: Environment | None = None) -> TemplateGraph:
    """Parse every template under ``templates/`` into a dependency graph."""
    env = env or Environment()
    graph = TemplateGraph()
    tdir = root / TEMPLATES_DIR
    for path in _list_templates(root):
        name = str(path.relative_to(tdir)).replace("\\", "/")
        source = path.read_text(encoding="utf-8")
        try:
            ast = env.parse(source)
            refs = {r for r in meta.find_referenced_templates(ast) if r}
        except Exception:
            refs = set()
        graph.refs[name] = refs
    return graph
