"""Unit tests for `errors.py`: shared helpers for user-facing messages."""

from __future__ import annotations

import pytest

from cuttlefish.errors import CuttlefishError, describe_os_error, read_text


def test_read_text_reports_non_utf8_with_line(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "post.md"
    path.write_bytes(b"+++\ntitle = 'x'\n\xff\n")
    with pytest.raises(CuttlefishError, match=r"^post\.md:3: not valid UTF-8"):
        read_text(path, CuttlefishError)


def test_read_text_keeps_universal_newlines(tmp_path):
    path = tmp_path / "post.md"
    path.write_bytes(b"a\r\nb\r\n")
    assert read_text(path, CuttlefishError) == "a\nb\n"


def test_describe_os_error_is_relative_and_untyped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(OSError) as exc:
        (tmp_path / "missing.txt").read_text()
    assert describe_os_error(exc.value) == "No such file or directory: missing.txt"
