"""Scaffold a new site by copying the bundled starter site."""

from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console

SITE_TEMPLATE_DIR = Path(__file__).parent / "site"


def scaffold_site(directory: Path, *, force: bool = False, console: Console | None = None) -> None:
    """Copy the starter site into *directory*."""
    console = console or Console()
    directory = directory.resolve()

    if directory.exists() and any(directory.iterdir()) and not force:
        console.print(
            f"[red]Refusing to scaffold:[/red] {directory} is not empty. "
            "Pass --force to override."
        )
        raise SystemExit(1)

    for src in SITE_TEMPLATE_DIR.rglob("*"):
        rel = src.relative_to(SITE_TEMPLATE_DIR)
        dest = directory / rel
        if src.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    _link_claude_md(directory)

    console.print(f"[green]Created site[/green] in {directory}")
    console.print("Next: [bold]cd {0} && ass serve[/bold]".format(directory.name))


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
