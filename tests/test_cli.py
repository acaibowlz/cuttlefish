"""Unit tests for `cli.py`."""

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

from typer.testing import CliRunner

from cuttlefish.cli import app


def test_version_flag_prints_package_version():
    for flag in ("--version", "-V"):
        result = CliRunner().invoke(app, [flag])
        assert result.exit_code == 0
        assert result.output.strip() == f"ctf {version('cuttlefish-ssg')}"


def test_os_error_is_a_clean_diagnostic(site: Path, monkeypatch):
    # An environment problem (here: `public` is a file) is user-fixable, so it
    # prints like any other error instead of a traceback.
    monkeypatch.chdir(site)
    (site / "public").write_text("", encoding="utf-8")
    result = CliRunner().invoke(app, ["build"])
    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "File system error" in result.output
    assert "Not a directory: public" in result.output


def test_init_refuses_non_empty_directory(tmp_path: Path):
    (tmp_path / "keep.txt").write_text("x", encoding="utf-8")
    result = CliRunner().invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 1
    assert "Refusing to scaffold" in result.output
    assert "Pass --force to override." in result.output


def test_build_verbose_lists_files(site: Path, monkeypatch):
    # The counts alone by default; -v adds the paths behind each count.
    monkeypatch.chdir(site)
    quiet = CliRunner().invoke(app, ["build", "--force"])
    loud = CliRunner().invoke(app, ["build", "--force", "-v"])
    assert quiet.exit_code == loud.exit_code == 0
    assert "blog/front-matter/" not in quiet.output
    assert "blog/front-matter/" in loud.output
    assert "css/main.css" in loud.output
