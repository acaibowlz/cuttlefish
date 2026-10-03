"""Unit tests for `scaffold/__init__.py`."""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from cuttlefish.scaffold import SITE_TEMPLATE_DIR, ScaffoldError, update_site

QUIET = Console(quiet=True)


def test_init_ships_customization_and_no_claude_md(site: Path):
    assert (site / "CUSTOMIZATION.md").is_file()
    assert not (site / "CLAUDE.md").exists()


def test_update_replaces_stale_agents_md_and_keeps_a_backup(site: Path):
    (site / "AGENTS.md").write_text("old guide with my notes\n", encoding="utf-8")
    update_site(site, console=QUIET)
    assert (site / "AGENTS.md").read_bytes() == (SITE_TEMPLATE_DIR / "AGENTS.md").read_bytes()
    assert (site / "AGENTS.md.bak").read_text(encoding="utf-8") == "old guide with my notes\n"


def test_update_is_a_no_op_when_current(site: Path):
    update_site(site, console=QUIET)
    assert not (site / "AGENTS.md.bak").exists()


def test_update_creates_customization_but_never_overwrites_it(site: Path):
    (site / "CUSTOMIZATION.md").unlink()
    update_site(site, console=QUIET)
    assert (site / "CUSTOMIZATION.md").is_file()

    (site / "CUSTOMIZATION.md").write_text("mine\n", encoding="utf-8")
    update_site(site, console=QUIET)
    assert (site / "CUSTOMIZATION.md").read_text(encoding="utf-8") == "mine\n"


def test_update_refuses_outside_a_site(tmp_path: Path):
    with pytest.raises(ScaffoldError, match="no config.toml"):
        update_site(tmp_path, console=QUIET)
    assert not (tmp_path / "AGENTS.md").exists()
