"""Cactbot data client with local caching."""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any

import httpx

from xiv_timeline.models import (
    Expansion,
    EncounterType,
    Difficulty,
    resolve_boss_name,
    BOSS_NAME_MAPPING,
)


# Cache directory
CACHE_DIR = Path.home() / ".xiv_timeline" / "cactbot_cache"
CACHE_EXPIRY_DAYS = 7


class CactbotClient:
    """Client for fetching timeline data from cactbot GitHub repository."""

    BASE_URL = "https://raw.githubusercontent.com/OverlayPlugin/cactbot/main/ui/raidboss/data"

    def __init__(self, cache_dir: Path | None = None):
        """Initialize the client with optional cache directory."""
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()

    def _get_cache_path(self, expansion: str, encounter_type: str, filename: str) -> Path:
        """Get the local cache file path."""
        return self.cache_dir / expansion / encounter_type / filename

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if the cache file is still valid."""
        if not cache_path.exists():
            return False
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return datetime.now() - mtime < timedelta(days=CACHE_EXPIRY_DAYS)

    async def _fetch_file(self, url: str, cache_path: Path) -> str:
        """Fetch a file from GitHub, using cache if available."""
        if self._is_cache_valid(cache_path):
            return cache_path.read_text(encoding="utf-8")

        # Fetch from GitHub
        response = await self.http_client.get(url)
        response.raise_for_status()
        content = response.text

        # Ensure directory exists and save to cache
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(content, encoding="utf-8")

        return content

    async def list_encounters(
        self,
        expansion: Expansion | None = None,
        encounter_type: EncounterType | None = None,
    ) -> list[dict[str, Any]]:
        """List all available encounters in the cactbot repository."""
        encounters = []

        expansions = [expansion] if expansion else list(Expansion)
        encounter_types = [encounter_type] if encounter_type else [EncounterType.RAID, EncounterType.TRIAL, EncounterType.ULTIMATE]

        for exp in expansions:
            for enc_type in encounter_types:
                url = f"{self.BASE_URL}/{exp.value}/{enc_type.value}"
                try:
                    response = await self.http_client.get(url)
                    if response.status_code == 200:
                        # Parse directory listing
                        files = re.findall(r'href="/OverlayPlugin/cactbot/blob/main/ui/raidboss/data/[^"]+\.txt"', response.text)
                        for file in files:
                            match = re.search(r'/([^/]+)\.txt"', file)
                            if match:
                                filename = match.group(1)
                                encounters.append({
                                    "filename": filename,
                                    "expansion": exp.value,
                                    "expansion_name": exp.display_name,
                                    "type": enc_type.value,
                                })
                except Exception:
                    continue

        return encounters

    async def fetch_timeline(
        self,
        boss_name: str,
        expansion: str | None = None,
        encounter_type: str | None = None,
        difficulty: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch timeline data for a specific boss.

        Args:
            boss_name: Boss name or ID (e.g., "p12s", "Zodiark")
            expansion: Expansion code (e.g., "06-ew")
            encounter_type: Type of encounter (raid, trial, ultimate)
            difficulty: Difficulty (n, s, u)

        Returns:
            Dictionary containing timeline data
        """
        # Try to resolve boss name
        resolved = resolve_boss_name(boss_name)

        if resolved:
            expansion = expansion or resolved["expansion"].value
            encounter_type = encounter_type or resolved["type"].value
            difficulty = difficulty or resolved["difficulty"].value
            filename = f"{boss_name.lower()}.txt"
        else:
            # Use provided values or defaults
            expansion = expansion or "06-ew"
            encounter_type = encounter_type or "raid"
            difficulty = difficulty or "s"
            filename = f"{boss_name.lower()}.txt"

        url = f"{self.BASE_URL}/{expansion}/{encounter_type}/{filename}"
        cache_path = self._get_cache_path(expansion, encounter_type, filename)

        try:
            content = await self._fetch_file(url, cache_path)
        except httpx.HTTPStatusError as e:
            # Try without difficulty suffix
            filename_no_diff = re.sub(r'[nsu]$', '', boss_name.lower()) + ".txt"
            url = f"{self.BASE_URL}/{expansion}/{encounter_type}/{filename_no_diff}"
            cache_path = self._get_cache_path(expansion, encounter_type, filename_no_diff)
            content = await self._fetch_file(url, cache_path)

        # Parse the timeline
        timeline_data = self._parse_timeline(content, boss_name)

        return {
            "boss_name": boss_name,
            "expansion": expansion,
            "encounter_type": encounter_type,
            "difficulty": difficulty,
            "raw_content": content,
            "entries": timeline_data["entries"],
            "phases": timeline_data["phases"],
            "source_url": url,
        }

    def _parse_timeline(self, content: str, boss_name: str) -> dict[str, Any]:
        """Parse cactbot timeline text into structured data."""
        entries = []
        phases = []
        current_phase = {"name": "Phase 1", "start_time": 0.0, "entries": []}

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Check for phase markers
            if "--sync--" in line and ("targetable" in line or "untargetable" in line):
                # Phase transition
                if current_phase["entries"]:
                    phases.append(current_phase)
                    current_phase = {"name": f"Phase {len(phases) + 1}", "start_time": 0.0, "entries": []}
                continue

            # Parse timeline entry
            # Format: timestamp "Ability Name" Ability { params }
            match = re.match(r'^(\d+\.?\d*)\s+"([^"]+)"\s+(.+)$', line)
            if match:
                timestamp = float(match.group(1))
                ability_name = match.group(2)
                params_str = match.group(3)

                # Parse ability ID and source
                id_match = re.search(r'id:\s*"([^"]+)"', params_str)
                source_match = re.search(r'source:\s*"([^"]+)"', params_str)
                duration_match = re.search(r'duration\s+(\d+\.?\d*)', params_str)

                entry = {
                    "timestamp": timestamp,
                    "ability_name": ability_name,
                    "ability_id": id_match.group(1) if id_match else None,
                    "source": source_match.group(1) if source_match else None,
                    "duration": float(duration_match.group(1)) if duration_match else None,
                    "raw_line": line,
                }

                entries.append(entry)
                current_phase["entries"].append(entry)

        # Add final phase
        if current_phase["entries"]:
            phases.append(current_phase)

        return {
            "entries": entries,
            "phases": phases,
        }

    async def fetch_boss_list(self) -> list[str]:
        """Fetch a list of all available boss IDs."""
        bosses = []
        for boss_id, info in BOSS_NAME_MAPPING.items():
            bosses.append(boss_id)
        return bosses
