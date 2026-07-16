"""Build manifest: hashing and load/save of ``.ctf/cache.json``.

The manifest records what was built last time so the next build can skip work.
Milestone 1 (hybrid) uses ``config_hash``, per-content hashes, template hashes,
and static hashes. Milestone 2 extends content entries with fingerprints.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

CACHE_DIR = ".ctf"
CACHE_FILE = "cache.json"
MANIFEST_VERSION = 3


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    return hash_bytes(text.encode("utf-8"))


def hash_file(path: Path) -> str:
    return hash_bytes(path.read_bytes())


@dataclass
class Manifest:
    """Everything the previous build recorded, for change detection."""

    version: int = MANIFEST_VERSION
    config_hash: str = ""
    #: source_rel -> {"hash", "outputs": [...], plus M2 fingerprints}
    content: dict[str, dict] = field(default_factory=dict)
    #: template name -> {"hash", "refs": [...]}
    templates: dict[str, dict] = field(default_factory=dict)
    #: static src_rel -> {"hash", "output"}
    static: dict[str, dict] = field(default_factory=dict)
    #: aggregate key -> {"fingerprint", "template", "outputs": [...]}
    aggregates: dict[str, dict] = field(default_factory=dict)
    #: error-page template name (e.g. "404.html") -> {"output"}
    error_pages: dict[str, dict] = field(default_factory=dict)

    # -- derived -----------------------------------------------------------

    def all_outputs(self) -> set[str]:
        """Every output file this manifest knows about (for pruning)."""
        outputs = self.page_outputs()
        for entry in self.static.values():
            out = entry.get("output")
            if out:
                outputs.add(out)
        for entry in self.error_pages.values():
            out = entry.get("output")
            if out:
                outputs.add(out)
        return outputs

    def page_outputs(self) -> set[str]:
        """HTML page outputs (content + aggregates), excluding static assets.

        Error pages (``404.html``) are deliberately excluded: they are not
        crawlable pages and must never appear in the sitemap.
        """
        outputs: set[str] = set()
        for entry in self.aggregates.values():
            outputs.update(entry.get("outputs", []))
        for entry in self.content.values():
            outputs.update(entry.get("outputs", []))
        return outputs

    # -- serialisation -----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "config_hash": self.config_hash,
            "content": self.content,
            "templates": self.templates,
            "static": self.static,
            "aggregates": self.aggregates,
            "error_pages": self.error_pages,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Manifest:
        return cls(
            version=data.get("version", MANIFEST_VERSION),
            config_hash=data.get("config_hash", ""),
            content=data.get("content", {}),
            templates=data.get("templates", {}),
            static=data.get("static", {}),
            aggregates=data.get("aggregates", {}),
            error_pages=data.get("error_pages", {}),
        )


def manifest_path(root: Path) -> Path:
    return root / CACHE_DIR / CACHE_FILE


def load_manifest(root: Path) -> Manifest | None:
    """Load the manifest, or ``None`` if absent/unreadable/incompatible."""
    path = manifest_path(root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("version") != MANIFEST_VERSION:
        return None
    return Manifest.from_dict(data)


def save_manifest(root: Path, manifest: Manifest) -> None:
    path = manifest_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
