"""Simple JSON cache helpers for encounter research."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _slugify(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in value)
    compact = "-".join(part for part in safe.split("-") if part)
    if compact:
        return compact[:80]
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


class ResearchCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, section: str, key: str) -> Path:
        section_dir = self.cache_dir / section
        section_dir.mkdir(parents=True, exist_ok=True)
        return section_dir / f"{_slugify(key)}.json"

    def load_json(self, section: str, key: str) -> Any | None:
        path = self._path(section, key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_json(self, section: str, key: str, payload: Any) -> Path:
        path = self._path(section, key)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
