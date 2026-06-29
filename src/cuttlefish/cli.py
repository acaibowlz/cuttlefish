"""Command-line interface for cuttlefish.

Three commands: ``init`` scaffolds a new site, ``build`` renders it to
``public/``, and ``serve`` runs a live-reloading dev server.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

import typer
from rich.padding import Padding

from cuttlefish.errors import CuttlefishError
from cuttlefish.ui import console, err_console, print_error

try:  # Typer >= 0.26 vendors its own copy of click under typer._click
    from typer._click import exceptions as click_exc
except ModuleNotFoundError:  # older Typer uses the standalone click package
    from click import exceptions as click_exc

app = typer.Typer(
    add_completion=False,
    help="cuttlefish — agentic static site generator.",
    no_args_is_help=True,
    # Flat help: rich_markup_mode=None makes Typer render --help with plain
    # Click formatting (Usage/Options/Commands) instead of Rich's boxed panels,
    # matching our flat `error:` diagnostics. Our own error rendering (see main)
    # bypasses Typer's error path, so disabling Rich markup has no other effect.
    rich_markup_mode=None,
)

T = TypeVar("T")


def handle_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Turn user-facing ``CuttlefishError``s into a clean message + exit code.

    These errors describe something the user can fix, so we print a concise,
    styled diagnostic instead of dumping a Python traceback. Bugs (anything that
    is not a ``CuttlefishError``) are left to propagate as normal.
    """

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> T:
        try:
            return func(*args, **kwargs)
        except CuttlefishError as exc:
            print_error(exc.summary, exc.detail)
            raise typer.Exit(1) from exc

    return wrapper


@app.command()
@handle_errors
def init(
    directory: Path = typer.Argument(..., help="Directory to create the new site in."),
    force: bool = typer.Option(False, "--force", help="Scaffold even if the directory is non-empty."),
) -> None:
    """Scaffold a new site."""
    from cuttlefish.scaffold import scaffold_site

    scaffold_site(directory, force=force, console=console)


@app.command()
@handle_errors
def build(
    root: Path = typer.Argument(Path("."), help="Site root (contains config.toml)."),
    force: bool = typer.Option(False, "--force", "--clean", help="Ignore the cache and rebuild everything."),
    drafts: bool = typer.Option(False, "--drafts", help="Include content marked draft = true."),
) -> None:
    """Build the site into public/."""
    from cuttlefish.build import build_site

    build_site(root, force=force, drafts=drafts, console=console)


@app.command()
@handle_errors
def serve(
    root: Path = typer.Argument(Path("."), help="Site root (contains config.toml)."),
    port: int = typer.Option(8000, "--port", "-p", help="Port to serve on."),
    drafts: bool = typer.Option(True, "--drafts/--no-drafts", help="Include drafts (default on in serve)."),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Watch + live-reload the browser."),
) -> None:
    """Serve public/ with watch + live reload."""
    from cuttlefish.serve import serve_site

    serve_site(root, port=port, drafts=drafts, reload=reload, console=console)


def main() -> None:
    """Entry point that renders Click usage errors in our flat ``error:`` style.

    Typer/Click normally show usage errors (missing argument, unknown option) in
    a boxed Rich panel. We run the command with ``standalone_mode=False`` so that
    rendering is skipped and the error is raised to us instead, then print it the
    same way :func:`print_error` prints a ``CuttlefishError`` — keeping every
    diagnostic in one visual language. ``CuttlefishError``s are already handled
    inside the commands (see :func:`handle_errors`) and surface here only as the
    exit code Click returns; genuine bugs propagate as a normal traceback.
    """
    command = typer.main.get_command(app)
    try:
        exit_code = command(standalone_mode=False)
    except click_exc.UsageError as exc:
        print_error(exc.format_message())
        if exc.ctx is not None:
            hint = f"try '{exc.ctx.command_path} --help' for help"
            err_console.print(Padding(hint, (0, 0, 0, 2), expand=False, style="dim"))
        raise SystemExit(exc.exit_code or 2) from exc
    except click_exc.ClickException as exc:
        print_error(exc.format_message())
        raise SystemExit(exc.exit_code or 1) from exc
    except click_exc.Abort:
        err_console.print("[dim]aborted[/dim]")
        raise SystemExit(130) from None
    raise SystemExit(exit_code or 0)


if __name__ == "__main__":
    main()
