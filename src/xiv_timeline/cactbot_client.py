"""Cactbot data client with local caching."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from xiv_timeline.models import (
    BOSS_NAME_MAPPING,
    Difficulty,
    Expansion,
    EncounterType,
    MULTI_HIT_TIME_THRESHOLD,
    resolve_boss_name,
)

# Cache directory
CACHE_DIR = Path.home() / ".xiv_timeline" / "cactbot_cache"
CACHE_EXPIRY_DAYS = 7

# Cactbot marker pattern: entries like --sync--, --Reset--, --north--, etc.
_MARKER_PATTERN = re.compile(r"^--.*--$")


def is_phase_marker(ability_name: str) -> bool:
    """Return True if this entry is a phase-related sync marker (kept in timeline)."""
    return ability_name == "--sync--"


def is_cosmetic_marker(ability_name: str) -> bool:
    """Return True if this entry is a cosmetic/positional marker (filtered out).

    Matches ``--Reset--``, ``--north--``, ``--intercardinal--``,
    ``--targetable--``, ``--untargetable--``, ``--hot jump--``, etc.
    The only ``--*--`` pattern we keep is ``--sync--``.
    """
    if not _MARKER_PATTERN.match(ability_name):
        return False
    return ability_name != "--sync--"


class CactbotClient:
    """Client for fetching timeline data from the cactbot GitHub repository."""

    BASE_URL = (
        "https://raw.githubusercontent.com/OverlayPlugin/cactbot"
        "/main/ui/raidboss/data"
    )

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.http_client.aclose()

    # ------------------------------------------------------------------
    # Caching helpers
    # ------------------------------------------------------------------

    def _cache_path(self, expansion: str, encounter_type: str, filename: str) -> Path:
        return self.cache_dir / expansion / encounter_type / filename

    def _is_cache_valid(self, path: Path) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return datetime.now() - mtime < timedelta(days=CACHE_EXPIRY_DAYS)

    async def _fetch_file(self, url: str, cache_path: Path) -> str:
        """Fetch a file from GitHub, using local cache when available."""
        if self._is_cache_valid(cache_path):
            return cache_path.read_text(encoding="utf-8")

        response = await self.http_client.get(url)
        response.raise_for_status()
        content = response.text

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(content, encoding="utf-8")
        return content

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch_timeline(
        self,
        boss_name: str,
        expansion: str | None = None,
        encounter_type: str | None = None,
        difficulty: str | None = None,
    ) -> dict[str, Any]:
        """Fetch and parse a boss timeline from the cactbot repository.

        Returns a dict with keys: boss_name, expansion, encounter_type,
        difficulty, raw_content, entries, phases, source_url.
        """
        resolved = resolve_boss_name(boss_name)

        if resolved:
            expansion = expansion or resolved["expansion"].value
            encounter_type = encounter_type or resolved["type"].value
            difficulty = difficulty or resolved["difficulty"].value
            filename = f"{resolved.get('cactbot_id', boss_name.lower())}.txt"
        else:
            expansion = expansion or "06-ew"
            encounter_type = encounter_type or "raid"
            difficulty = difficulty or "s"
            filename = f"{boss_name.lower()}.txt"

        url = f"{self.BASE_URL}/{expansion}/{encounter_type}/{filename}"
        cache = self._cache_path(expansion, encounter_type, filename)

        try:
            content = await self._fetch_file(url, cache)
        except httpx.HTTPStatusError:
            # Retry without difficulty suffix
            base = filename.removesuffix(".txt")
            alt_filename = re.sub(r"[nsu]$", "", base) + ".txt"
            url = f"{self.BASE_URL}/{expansion}/{encounter_type}/{alt_filename}"
            cache = self._cache_path(expansion, encounter_type, alt_filename)
            content = await self._fetch_file(url, cache)

        parsed = self._parse_timeline(content)

        return {
            "boss_name": boss_name,
            "expansion": expansion,
            "encounter_type": encounter_type,
            "difficulty": difficulty,
            "raw_content": content,
            "entries": parsed["entries"],
            "phases": parsed["phases"],
            "source_url": url,
        }

    async def fetch_boss_list(self) -> list[str]:
        """Return all known boss IDs."""
        return list(BOSS_NAME_MAPPING.keys())

    # ------------------------------------------------------------------
    # Timeline parsing
    # ------------------------------------------------------------------

    # Regex: ``12.3 "Ability Name" ...params...``
    _ENTRY_RE = re.compile(r'^(\d+\.?\d*)\s+"([^"]+)"\s+(.+)$')

    def _parse_timeline(self, content: str) -> dict[str, Any]:
        """Parse cactbot timeline text into structured entries and phases.

        Phase boundaries are determined by ``--sync--`` entries that coincide
        with ``targetable`` / ``untargetable`` markers in the raw content.
        Cosmetic markers (``--north--``, ``--Reset--``, etc.) are filtered out
        so only real boss abilities and phase syncs remain.
        """
        all_entries: list[dict[str, Any]] = []
        phases: list[dict[str, Any]] = []
        current_phase: dict[str, Any] = {
            "name": "Phase 1",
            "start_time": 0.0,
            "entries": [],
        }

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Detect phase transitions via targetable/untargetable sync lines
            if "--sync--" in line and ("targetable" in line or "untargetable" in line):
                if current_phase["entries"]:
                    phases.append(current_phase)
                    current_phase = {
                        "name": f"Phase {len(phases) + 1}",
                        "start_time": 0.0,
                        "entries": [],
                    }
                continue

            match = self._ENTRY_RE.match(line)
            if not match:
                continue

            timestamp = float(match.group(1))
            ability_name = match.group(2)
            params_str = match.group(3)

            # Skip cosmetic markers (--north--, --Reset--, etc.)
            if is_cosmetic_marker(ability_name):
                continue

            # Skip cast start actions to only keep the damage/resolution
            if ability_name.endswith("(cast)") or " (cast)" in ability_name:
                continue

            entry = {
                "timestamp": timestamp,
                "ability_name": ability_name,
                "raw_line": line,
                "hit_count": 1,
                "is_multi_hit": False,
            }

            all_entries.append(entry)
            current_phase["entries"].append(entry)

        # Flush last phase
        if current_phase["entries"]:
            phases.append(current_phase)

        # Group consecutive same-name abilities within threshold
        grouped = self._group_multi_hits(all_entries)

        # Rebuild phases using the grouped entries
        phases = self._rebuild_phases(phases, grouped)

        return {"entries": grouped, "phases": phases}

    # ------------------------------------------------------------------
    # Multi-hit grouping
    # ------------------------------------------------------------------

    def _group_multi_hits(
        self, entries: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Mark consecutive same-name entries within the time threshold."""
        if not entries:
            return entries

        grouped: list[dict[str, Any]] = []
        current_group: list[dict[str, Any]] = [entries[0]]

        for entry in entries[1:]:
            prev = current_group[-1]
            same_name = entry["ability_name"] == prev["ability_name"]
            within_threshold = (
                entry["timestamp"] - prev["timestamp"] <= MULTI_HIT_TIME_THRESHOLD
            )

            if same_name and within_threshold:
                current_group.append(entry)
            else:
                grouped.extend(self._finalize_group(current_group))
                current_group = [entry]

        grouped.extend(self._finalize_group(current_group))
        return grouped

    @staticmethod
    def _finalize_group(group: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Annotate a group of entries with multi-hit metadata."""
        if len(group) == 1:
            return group

        hit_count = len(group)
        first_ts = group[0]["timestamp"]
        last_ts = group[-1]["timestamp"]

        for entry in group:
            entry["hit_count"] = hit_count
            entry["is_multi_hit"] = True
            entry["first_timestamp"] = first_ts
            entry["last_timestamp"] = last_ts
            entry["time_span"] = last_ts - first_ts

        return group

    @staticmethod
    def _rebuild_phases(
        original_phases: list[dict[str, Any]],
        grouped_entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Re-slot grouped entries back into phases by timestamp range."""
        if not grouped_entries or not original_phases:
            return original_phases

        new_phases: list[dict[str, Any]] = []
        for phase in original_phases:
            phase_entries = phase.get("entries", [])
            if not phase_entries:
                continue

            phase_start = phase_entries[0]["timestamp"]
            phase_end = phase_entries[-1]["timestamp"]

            matched = [
                e
                for e in grouped_entries
                if phase_start <= e["timestamp"] <= phase_end
            ]
            if matched:
                new_phases.append({
                    "name": phase["name"],
                    "start_time": phase_start,
                    "entries": matched,
                })

        return new_phases
