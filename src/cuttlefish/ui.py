"""Shared terminal output: consoles and the diagnostic vocabulary.

One place owns how cuttlefish talks to the terminal so every command speaks the
same language:

- **status** uses glyphs — ``✓`` (built), ``↻`` (rebuilt) — printed by the
  build/serve code directly on :data:`console`.
- **diagnostics** use keyword prefixes — ``error:`` (and, in future,
  ``warning:``) — printed by :func:`print_error` on :data:`err_console`.

The keyword style matches the wider ecosystem (cargo, ruff, uv): the *word*
carries the severity, so meaning survives ``--no-color``, CI logs, and
color-blindness, with color as enhancement rather than the signal. It also lets
us render Typer/Click usage errors the same way instead of Rich's boxed panel
(see ``cli.main``).
"""

from __future__ import annotations

from rich.console import Console
from rich.markup import escape
from rich.padding import Padding

#: Normal output (stdout): status lines, the serve banner, scaffold next-steps.
console = Console()
#: Diagnostics (stderr). ``highlight=False`` so paths/values aren't recolored.
err_console = Console(stderr=True, highlight=False)


def print_error(summary: str, detail: str | None = None) -> None:
    """Print a flat ``error:`` diagnostic, optionally with an indented detail.

    Two tiers, Zola-style: a headline naming what failed, then the specific
    reason beneath it. Text is escaped because messages routinely contain
    bracketed config locations like ``[content_types.blog]`` that Rich would
    otherwise parse as markup.
    """
    err_console.print(f"[bold red]error:[/bold red] {escape(summary)}")
    if detail and detail != summary:
        err_console.print(Padding(escape(detail), (0, 0, 0, 2), expand=False))
