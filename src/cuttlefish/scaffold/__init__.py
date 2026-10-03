"""Scaffold a new site by copying the bundled starter site."""

from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console

from cuttlefish.errors import CuttlefishError, display_path

SITE_TEMPLATE_DIR = Path(__file__).parent / "site"


class ScaffoldError(CuttlefishError):
    """Raised when the starter site cannot be created."""

    default_summary = "Refusing to scaffold"


def scaffold_site(directory: Path, *, force: bool = False, console: Console | None = None) -> None:
    """Copy the starter site into *directory*."""
    console = console or Console()
    directory = directory.resolve()

    if directory.exists() and any(directory.iterdir()) and not force:
        raise ScaffoldError(f"{display_path(directory)} is not empty. Pass --force to override.")

    for src in SITE_TEMPLATE_DIR.rglob("*"):
        rel = src.relative_to(SITE_TEMPLATE_DIR)
        dest = directory / rel
        if src.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    url = "http://127.0.0.1:8000/"
    console.print(f"[green]✓[/green] Created a new cuttlefish site in [bold]{directory}[/bold]")
    console.print()
    console.print("  To get started, run:")
    console.print()
    console.print(f"    [bold cyan]cd {directory}[/bold cyan]")
    console.print("    [bold cyan]ctf serve[/bold cyan]")
    console.print()
    console.print(f"  Your site will be live at [link={url}]{url}[/link] with live reload.")
    console.print("  [dim]Customize it in config.toml, or read AGENTS.md for the full guide.[/dim]")


def update_site(root: Path, *, console: Console | None = None) -> None:
    """Replace the site's ``AGENTS.md`` with the guide for this version of ctf.

    ``AGENTS.md`` is generator-owned; site-specific notes live in
    ``CUSTOMIZATION.md``, so a plain overwrite is safe. Sites from before that
    split may have notes inside ``AGENTS.md``, so a copy that differs is kept as
    ``AGENTS.md.bak`` rather than lost.
    """
    console = console or Console()
    root = root.resolve()
    if not (root / "config.toml").is_file():
        raise ScaffoldError(
            f"{display_path(root)} has no config.toml. Run this from a site root, or pass its path.",
            summary="Refusing to update",
        )

    agents = root / "AGENTS.md"
    new = (SITE_TEMPLATE_DIR / "AGENTS.md").read_bytes()
    changed = not agents.is_file() or agents.read_bytes() != new
    if changed:
        if agents.is_file():
            shutil.copy2(agents, root / "AGENTS.md.bak")
            console.print("[dim]Previous AGENTS.md saved as AGENTS.md.bak[/dim]")
        agents.write_bytes(new)

    # Older sites predate CUSTOMIZATION.md; the new AGENTS.md tells the agent
    # to read it, so give them the starter file. Never overwrite an existing one.
    custom = root / "CUSTOMIZATION.md"
    if not custom.exists():
        shutil.copy2(SITE_TEMPLATE_DIR / "CUSTOMIZATION.md", custom)
        console.print("[green]✓[/green] Created CUSTOMIZATION.md")

    if changed:
        console.print("[green]✓[/green] Updated AGENTS.md")
    else:
        console.print("[green]✓[/green] AGENTS.md is up to date")
