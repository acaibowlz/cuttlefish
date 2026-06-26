"""Command-line interface for ass.

Three commands: ``init`` scaffolds a new site, ``build`` renders it to
``public/``, and ``serve`` runs a live-reloading dev server.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import typer
from rich.console import Console
from rich.markup import escape
from rich.padding import Padding

from ass.errors import AssError

app = typer.Typer(
    add_completion=False,
    help="ass — agentic static site generator.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True, highlight=False)

T = TypeVar("T")


def handle_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Turn user-facing ``AssError``s into a clean message + exit code.

    These errors describe something the user can fix, so we print a concise,
    styled line to stderr instead of dumping a Python traceback. Bugs (anything
    that is not an ``AssError``) are left to propagate as normal.
    """

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> T:
        try:
            return func(*args, **kwargs)
        except AssError as exc:
            # Zola-style two tiers: a headline naming the operation that failed,
            # then the specific reason indented beneath it. Match the SSG's glyph
            # style (✓/✗/↻ used by init, build, serve). Escape the text: messages
            # routinely contain bracketed config locations like
            # "[content_types.blog]" that Rich would otherwise parse as markup.
            err_console.print(f"[red]✗[/red] {escape(exc.summary)}")
            if exc.detail and exc.detail != exc.summary:
                err_console.print(Padding(escape(exc.detail), (0, 0, 0, 2)))
            raise typer.Exit(1) from exc

    return wrapper


@app.command()
@handle_errors
def init(
    directory: Path = typer.Argument(..., help="Directory to create the new site in."),
    force: bool = typer.Option(False, "--force", help="Scaffold even if the directory is non-empty."),
) -> None:
    """Scaffold a new site."""
    from ass.scaffold import scaffold_site

    scaffold_site(directory, force=force, console=console)


@app.command()
@handle_errors
def build(
    root: Path = typer.Argument(Path("."), help="Site root (contains config.toml)."),
    force: bool = typer.Option(False, "--force", "--clean", help="Ignore the cache and rebuild everything."),
    drafts: bool = typer.Option(False, "--drafts", help="Include content marked draft = true."),
) -> None:
    """Build the site into ``public/``."""
    from ass.build import build_site

    build_site(root, force=force, drafts=drafts, console=console)


@app.command()
@handle_errors
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
