"""Command-line interface for ass.

Three commands: ``init`` scaffolds a new site, ``build`` renders it to
``public/``, and ``serve`` runs a live-reloading dev server.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    add_completion=False,
    help="ass — agentic static site generator.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def init(
    directory: Path = typer.Argument(..., help="Directory to create the new site in."),
    force: bool = typer.Option(False, "--force", help="Scaffold even if the directory is non-empty."),
) -> None:
    """Scaffold a new site."""
    from ass.scaffold import scaffold_site

    scaffold_site(directory, force=force, console=console)


@app.command()
def build(
    root: Path = typer.Argument(Path("."), help="Site root (contains config.toml)."),
    force: bool = typer.Option(False, "--force", "--clean", help="Ignore the cache and rebuild everything."),
    drafts: bool = typer.Option(False, "--drafts", help="Include content marked draft = true."),
) -> None:
    """Build the site into ``public/``."""
    from ass.build import build_site

    build_site(root, force=force, drafts=drafts, console=console)


@app.command()
def serve(
    root: Path = typer.Argument(Path("."), help="Site root (contains config.toml)."),
    port: int = typer.Option(8000, "--port", "-p", help="Port to serve on."),
    drafts: bool = typer.Option(True, "--drafts/--no-drafts", help="Include drafts (default on in serve)."),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Watch + live-reload the browser."),
) -> None:
    """Serve ``public/`` with watch + live reload."""
    from ass.serve import serve_site

    serve_site(root, port=port, drafts=drafts, reload=reload, console=console)


if __name__ == "__main__":
    app()
