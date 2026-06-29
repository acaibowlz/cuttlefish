"""Shared fixtures: a freshly scaffolded site in a temp directory."""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from cuttlefish.build import build_site
from cuttlefish.scaffold import scaffold_site


@pytest.fixture
def site(tmp_path: Path) -> Path:
    """Scaffold the starter site into a temp dir and return its root."""
    root = tmp_path / "site"
    root.mkdir()
    scaffold_site(root, force=True, console=Console(quiet=True))
    return root


@pytest.fixture
def build():
    """Return a helper that builds a site quietly and returns BuildStats."""

    def _build(root: Path, **kwargs):
        return build_site(root, console=Console(quiet=True), **kwargs)

    return _build


def read(root: Path, rel: str) -> str:
    return (root / "public" / rel).read_text(encoding="utf-8")


def append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text)
