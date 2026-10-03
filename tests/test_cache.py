"""Unit tests for `cache.py`: loading the build manifest."""

from __future__ import annotations

from cuttlefish.cache import load_manifest, manifest_path


def test_load_manifest_ignores_wrong_shape(tmp_path):
    # Valid JSON that is not a manifest is as unusable as corrupt JSON: rebuild.
    path = manifest_path(tmp_path)
    path.parent.mkdir()
    path.write_text("[1, 2]", encoding="utf-8")
    assert load_manifest(tmp_path) is None
