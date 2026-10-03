"""Shared base for user-facing errors.

Errors that subclass :class:`CuttlefishError` describe a problem the user can fix
(a bad config, an unparseable content file, a failed render). The CLI catches
them and prints a concise, styled message instead of a traceback; anything that
is *not* an ``CuttlefishError`` is a bug and should surface in full.

Each error carries two tiers, Zola-style: a ``summary`` naming the operation
that failed ("Failed to load config", "Failed to render blog/index.md") and a
``detail`` giving the specific reason. The CLI prints the summary as a headline
and the detail beneath it.
"""

from __future__ import annotations

from pathlib import Path


class CuttlefishError(Exception):
    """Base class for user-facing errors, shown as headline + detail, not a traceback.

    Pass ``detail`` positionally (the specific reason). ``summary`` names the
    failed operation; when omitted it falls back to the subclass's
    ``default_summary``. ``str()`` returns just the detail, so existing call
    sites that interpolate the exception keep their concise message.
    """

    #: Headline used when a raise site does not pass an explicit ``summary``.
    default_summary = "Something went wrong"

    def __init__(self, detail: str, *, summary: str | None = None) -> None:
        self.detail = str(detail)
        self.summary = summary or self.default_summary
        super().__init__(self.detail)


def display_path(path: Path | str) -> str:
    """*path* relative to the working directory when under it, for messages."""
    try:
        return Path(path).resolve().relative_to(Path.cwd()).as_posix()
    except ValueError:
        return str(path)


def describe_os_error(exc: OSError) -> str:
    """``Permission denied: static/x.txt`` rather than ``[Errno 13] … PosixPath(...)``."""
    reason = exc.strerror or str(exc)
    return f"{reason}: {display_path(exc.filename)}" if exc.filename else reason


def read_text(path: Path, error: type[CuttlefishError], **kwargs: str) -> str:
    """Read a user-authored file as UTF-8, raising *error* (not a traceback) if it isn't."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        line = path.read_bytes()[: exc.start].count(b"\n") + 1
        raise error(
            f"{display_path(path)}:{line}: not valid UTF-8 text. Re-save the file as UTF-8.",
            **kwargs,
        ) from exc
