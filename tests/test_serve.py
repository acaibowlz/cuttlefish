"""Unit tests for `serve.py`: mapping a request target to a file in public/."""

from __future__ import annotations

import socket

import pytest
from rich.console import Console

from cuttlefish.serve import ServeError, resolve_request, serve_site


def test_resolve_request_decodes_percent_encoded_unicode(tmp_path):
    # Browsers send Unicode slugs percent-encoded, but they land on disk as the
    # decoded characters — without unquoting, every non-ASCII page 404s.
    page = tmp_path / "blog" / "新貼文" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text("hi", encoding="utf-8")

    assert resolve_request(tmp_path, "/blog/%E6%96%B0%E8%B2%BC%E6%96%87/") == page
    assert resolve_request(tmp_path, "/blog/新貼文/") == page


def test_resolve_request_maps_directories_to_index(tmp_path):
    (tmp_path / "blog").mkdir()
    assert resolve_request(tmp_path, "/") == tmp_path / "index.html"
    assert resolve_request(tmp_path, "/blog") == tmp_path / "blog" / "index.html"
    assert resolve_request(tmp_path, "/css/main.css") == tmp_path / "css" / "main.css"


def test_resolve_request_rejects_traversal(tmp_path):
    (tmp_path / "public").mkdir()
    public = tmp_path / "public"
    (tmp_path / "secret.txt").write_text("no", encoding="utf-8")

    assert resolve_request(public, "/../secret.txt") is None
    # Encoded traversal must fail too: decoding happens before the check.
    assert resolve_request(public, "/%2e%2e/secret.txt") is None


def test_serve_reports_port_in_use(site):
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        with pytest.raises(ServeError, match=f"Port {port} is already in use"):
            serve_site(site, port=port, reload=False, console=Console(quiet=True))
