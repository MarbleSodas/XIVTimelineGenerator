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
    infer_target_type,
    MULTI_HIT_TIME_THRESHOLD,
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
                    # Multi-hit fields (will be populated after grouping)
                    "hit_count": 1,
                    "is_multi_hit": False,
                    "target_type": infer_target_type(ability_name).value if infer_target_type(ability_name) else "unknown",
                }

                entries.append(entry)
                current_phase["entries"].append(entry)

        # Add final phase
        if current_phase["entries"]:
            phases.append(current_phase)

        # Group consecutive same-name abilities within time threshold
        entries = self._group_consecutive_abilities(entries)
        
        # Update phases with grouped entries
        if current_phase["entries"]:
            phases.append(current_phase)
        
        # Rebuild phases with grouped entries
        phases = self._rebuild_phases_with_grouped_entries(phases, entries)

        return {
            "entries": entries,
            "phases": phases,
        }

    def _group_consecutive_abilities(self, entries):
        """Group consecutive same-name abilities within the time threshold."""
        if not entries:
            return entries
        
        grouped = []
        current_group = [entries[0]]
        
        for i in range(1, len(entries)):
            current = entries[i]
            prev = current_group[-1]
            
            # Check if same ability name
            if current["ability_name"] == prev["ability_name"]:
                # Check if within time threshold
                time_diff = current["timestamp"] - prev["timestamp"]
                if time_diff <= MULTI_HIT_TIME_THRESHOLD:
                    current_group.append(current)
                else:
                    # Time threshold exceeded, finalize current group
                    grouped.extend(self._create_grouped_entry(current_group))
                    current_group = [current]
            else:
                # Different ability, finalize current group
                grouped.extend(self._create_grouped_entry(current_group))
                current_group = [current]
        
        # Final group
        if current_group:
            grouped.extend(self._create_grouped_entry(current_group))
        
        return grouped

    def _create_grouped_entry(self, group):
        """Create grouped entry from a list of consecutive same-name abilities."""
        if len(group) == 1:
            return group
        
        # Mark all entries in group as multi-hit
        hit_count = len(group)
        first_entry = group[0]
        last_entry = group[-1]
        
        for entry in group:
            entry["hit_count"] = hit_count
            entry["is_multi_hit"] = True
            entry["first_timestamp"] = first_entry["timestamp"]
            entry["last_timestamp"] = last_entry["timestamp"]
            entry["time_span"] = last_entry["timestamp"] - first_entry["timestamp"]
        
        return group

    def _rebuild_phases_with_grouped_entries(self, original_phases, grouped_entries):
        """Rebuild phases with grouped entries while preserving phase structure."""
        if not grouped_entries:
            return original_phases
        
        # Get all entry timestamps
        entry_timestamps = [(e["timestamp"], e) for e in grouped_entries]
        
        # Rebuild phases
        new_phases = []
        for phase in original_phases:
            phase_start = phase.get("start_time", 0)
            phase_end = phase.get("end_time", float("inf"))
            
            # Filter entries that fall within this phase
            phase_entries = [
                e for ts, e in entry_timestamps 
                if phase_start <= ts <= phase_end or (phase_start == 0 and ts <= phase_end)
            ]
            
            if phase_entries:
                new_phase = phase.copy()
                new_phase["entries"] = phase_entries
                new_phases.append(new_phase)
        
        return new_phases

    async def fetch_boss_list(self) -> list[str]:
        """Fetch a list of all available boss IDs."""
        bosses = []
        for boss_id, info in BOSS_NAME_MAPPING.items():
            bosses.append(boss_id)
        return bosses
