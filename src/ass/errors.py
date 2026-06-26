"""Shared base for user-facing errors.

Errors that subclass :class:`AssError` describe a problem the user can fix
(a bad config, an unparseable content file, a failed render). The CLI catches
them and prints a concise, styled message instead of a traceback; anything that
is *not* an ``AssError`` is a bug and should surface in full.

Each error carries two tiers, Zola-style: a ``summary`` naming the operation
that failed ("Failed to load config", "Failed to render blog/index.md") and a
``detail`` giving the specific reason. The CLI prints the summary as a headline
and the detail beneath it.
"""

from __future__ import annotations


class AssError(Exception):
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
