"""Create a new content file from ``config.toml``.

``ctf new <type> <title>`` writes a ready-to-edit ``content/<type>/<slug>.md``
skeleton. The skeleton is *derived from config*: the required front matter for
the type (dated types need ``title``/``date``/``description``; the standalone
``pages`` type needs only a slug), plus each configured taxonomy as a commented
placeholder so the author can see what's available without polluting the term
index. The output is guaranteed to satisfy :func:`content.parse_item`, so a
freshly created file builds cleanly with no edits.

The command is deliberately non-interactive: everything is an argument or flag,
matching ``hugo new`` and ``jekyll post``. It is a human convenience and plays
no part in the site-authoring contract that ``AGENTS.md`` describes.
"""

from __future__ import annotations

import difflib
import os
import subprocess
from datetime import date as date_cls
from pathlib import Path

from rich.console import Console

from cuttlefish.config import PAGES_TYPE, load_config
from cuttlefish.content import CONTENT_DIR
from cuttlefish.errors import CuttlefishError
from cuttlefish.permalink import resolve_permalink, slugify


class NewContentError(CuttlefishError):
    """Raised when a new content file cannot be created."""

    default_summary = "Failed to create content"


#: Seeded when no ``--description`` is given. It must be *non-empty*: a dated
#: type's build rejects a blank description (see ``_require_front_matter``), so
#: an empty placeholder would produce a skeleton that fails to build. A visible
#: placeholder both builds and signals what to replace.
_PLACEHOLDER_DESCRIPTION = "A short description of this content."


def _toml_string(value: str) -> str:
    """Emit *value* as a single-line TOML basic string.

    Escapes the two characters that would break the string (``\\`` and ``"``)
    and folds any whitespace newlines/tabs to spaces so a pasted multi-line
    title still yields valid front matter.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    for ws in ("\r\n", "\r", "\n", "\t"):
        escaped = escaped.replace(ws, " ")
    return f'"{escaped}"'


def _skeleton(
    config,
    type_name: str,
    *,
    title: str,
    slug: str,
    description: str,
    date_value: date_cls,
    draft: bool,
) -> str:
    """Build the ``+++``-fenced front matter and body for a new file."""
    is_pages = type_name == PAGES_TYPE
    lines = ["+++", f"title = {_toml_string(title)}"]
    if is_pages:
        # Pages carry no date and are exempt from the dated-type requirements;
        # they just need a slug (mirrors the scaffold's about.md).
        lines.append(f"slug = {_toml_string(slug)}")
        if draft:
            lines.append("draft = true")
    else:
        lines.append(f"date = {date_value.isoformat()}")  # unquoted local date
        lines.append(f"description = {_toml_string(description or _PLACEHOLDER_DESCRIPTION)}")
        if draft:
            lines.append("draft = true")
        # Every configured taxonomy is offered as a commented placeholder: an
        # active placeholder term would leak into the term index, so keep it
        # inert until the author fills in real terms.
        for name, taxonomy in config.taxonomies.items():
            placeholder = '["example"]' if taxonomy.multiple else '"example"'
            lines.append(f"# {name} = {placeholder}")
    lines.append("+++")
    lines.append("")
    lines.append("Write your content here.")
    lines.append("")
    return "\n".join(lines)


def create_content(
    root: Path,
    type_name: str,
    title: str,
    *,
    slug: str | None = None,
    description: str = "",
    date: str | None = None,
    draft: bool = False,
    force: bool = False,
    edit: bool = False,
    console: Console | None = None,
) -> Path:
    """Create ``content/<type>/<slug>.md`` and return its path."""
    console = console or Console()
    root = root.resolve()

    config = load_config(root)
    if type_name not in config.content_types:
        valid = sorted(config.content_types)
        match = difflib.get_close_matches(type_name, valid, n=1)
        suggestion = f" Did you mean {match[0]!r}?" if match else ""
        raise NewContentError(
            f"Unknown content type {type_name!r}.{suggestion} "
            f"Valid types: {', '.join(valid) or '(none configured)'}."
        )

    if date is None:
        date_value = date_cls.today()
    else:
        try:
            date_value = date_cls.fromisoformat(date)
        except ValueError as exc:
            raise NewContentError(
                f"Invalid --date {date!r}; expected an ISO date like 2026-07-11."
            ) from exc

    # Always slugify so the filename and permalink are URL-safe, whether the
    # slug came from --slug or was derived from the title.
    final_slug = slugify(slug or title)
    dest = root / CONTENT_DIR / type_name / f"{final_slug}.md"
    rel = dest.relative_to(root)
    if dest.exists() and not force:
        raise NewContentError(f"{rel} already exists. Pass --force to overwrite.")

    content = _skeleton(
        config,
        type_name,
        title=title,
        slug=final_slug,
        description=description,
        date_value=date_value,
        draft=draft,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")

    content_type = config.content_types[type_name]
    url = resolve_permalink(
        content_type.permalink, date=date_value, slug=final_slug, type=type_name
    )
    console.print(f"[green]✓[/green] Created [bold]{rel}[/bold]")
    console.print(f"  It will be served at [bold cyan]{url}[/bold cyan]")

    if edit:
        editor = os.environ.get("EDITOR")
        if editor:
            subprocess.run([editor, str(dest)])
        else:
            console.print("  [dim]$EDITOR is not set; open the file manually to edit it.[/dim]")

    return dest
