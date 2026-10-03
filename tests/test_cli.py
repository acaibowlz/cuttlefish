"""Unit tests for `cli.py`."""

from __future__ import annotations

from importlib.metadata import version

from typer.testing import CliRunner

from cuttlefish.cli import app


def test_version_flag_prints_package_version():
    for flag in ("--version", "-V"):
        result = CliRunner().invoke(app, [flag])
        assert result.exit_code == 0
        assert result.output.strip() == f"ctf {version('cuttlefish-ssg')}"
