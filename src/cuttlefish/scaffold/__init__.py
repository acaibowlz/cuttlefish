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

    _link_claude_md(directory)

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


def _link_claude_md(directory: Path) -> None:
    """Point CLAUDE.md at AGENTS.md so Claude Code loads the agent guide.

    Created as a symlink; falls back to a copy where symlinks aren't permitted
    (e.g. unprivileged Windows).
    """
    agents = directory / "AGENTS.md"
    if not agents.exists():
        return
    claude = directory / "CLAUDE.md"
    if claude.is_symlink() or claude.exists():
        claude.unlink()
    try:
        claude.symlink_to("AGENTS.md")
    except (OSError, NotImplementedError):
        shutil.copy2(agents, claude)
