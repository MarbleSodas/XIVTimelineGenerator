"""Timeline synthesizer - merges cactbot data with guide information."""

import re
from datetime import datetime
from typing import Any


class TimelineSynthesizer:
    """Synthesizes enriched timeline from cactbot data and guide content."""

    def __init__(self):
        """Initialize the synthesizer."""
        pass

    def synthesize(
        self,
        cactbot_data: dict[str, Any],
        guide_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Synthesize timeline data with guide information.

        Args:
            cactbot_data: Raw timeline data from cactbot
            guide_data: Guide content from various sources

        Returns:
            Synthesized timeline with phases, variations, and notes
        """
        boss_name = cactbot_data["boss_name"]
        entries = cactbot_data.get("entries", [])
        phases = cactbot_data.get("phases", [])

        # Build enhanced phases with guide context
        enhanced_phases = self._enhance_phases(phases, guide_data)

        # Extract variations from guides
        variations = self._extract_variations(guide_data)

        # Generate notes
        notes = self._generate_notes(cactbot_data, guide_data)

        # Calculate confidence based on available data
        confidence = self._calculate_confidence(cactbot_data, guide_data)

        return {
            "boss_name": boss_name,
            "expansion": cactbot_data.get("expansion"),
            "encounter_type": cactbot_data.get("encounter_type"),
            "difficulty": cactbot_data.get("difficulty"),
            "phases": enhanced_phases,
            "variations": variations,
            "notes": notes,
            "confidence": confidence,
            "generated_at": datetime.now().isoformat(),
            "sources": {
                "cactbot": cactbot_data.get("source_url"),
                "guides": self._get_guide_sources(guide_data),
            },
        }

    def _enhance_phases(
        self,
        phases: list[dict[str, Any]],
        guide_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Enhance phase data with guide context."""
        enhanced = []

        for phase in phases:
            phase_name = phase.get("name", f"Phase {len(enhanced) + 1}")
            phase_entries = phase.get("entries", [])

            # Find matching guide content
            guide_phases = guide_data.get("guides", {}).get("icy-veins", {}).get("content", {}).get("phases", [])

            # Look for phase-specific tips
            phase_tips = []
            for guide_phase in guide_phases:
                if phase_name.lower() in guide_phase.get("title", "").lower():
                    phase_tips.append(guide_phase.get("content", ""))

            # Get first and last ability times
            first_ability = phase_entries[0] if phase_entries else None
            last_ability = phase_entries[-1] if phase_entries else None
            duration = None
            if first_ability and last_ability:
                duration = last_ability["timestamp"] - first_ability["timestamp"]

            enhanced.append({
                "name": phase_name,
                "start_time": first_ability["timestamp"] if first_ability else 0.0,
                "end_time": last_ability["timestamp"] if last_ability else 0.0,
                "duration": duration,
                "ability_count": len(phase_entries),
                "abilities": phase_entries,
                "tips": phase_tips,
            })

        return enhanced

    def _extract_variations(self, guide_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract phase skips and variations from guide content."""
        variations = []

        guides = guide_data.get("guides", {})

        # Check Icy Veins for variations
        icyveins = guides.get("icy-veins", {})
        if icyveins.get("success"):
            content = icyveins.get("content", {})
            for variation in content.get("variations", []):
                variations.append({
                    "source": "icy-veins",
                    "title": variation.get("title", ""),
                    "description": variation.get("description", ""),
                    "type": self._classify_variation(variation.get("description", "")),
                })

        # Check Hardcore Gamer
        hardcore = guides.get("hardcore-gamer", {})
        if hardcore.get("success"):
            content = hardcore.get("content", {})
            for variation in content.get("variations", []):
                variations.append({
                    "source": "hardcore-gamer",
                    "title": variation.get("title", ""),
                    "description": variation.get("description", ""),
                    "type": self._classify_variation(variation.get("description", "")),
                })

        return variations

    def _classify_variation(self, description: str) -> str:
        """Classify the type of variation."""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ["skip", "skipped"]):
            return "phase_skip"
        elif any(kw in desc_lower for kw in ["timing", "faster", "slower", "delay"]):
            return "timing"
        elif any(kw in desc_lower for kw in ["alternative", "different", "variant"]):
            return "strategy"
        elif any(kw in desc_lower for kw in ["enrage", " DPS", "kill"]):
            return "enrage_timing"
        else:
            return "general"

    def _generate_notes(
        self,
        cactbot_data: dict[str, Any],
        guide_data: dict[str, Any],
    ) -> list[str]:
        """Generate useful notes about the timeline."""
        notes = []

        entries = cactbot_data.get("entries", [])
        if not entries:
            return ["No timeline entries found"]

        # Get overall timeline duration
        first_entry = entries[0]
        last_entry = entries[-1]
        total_duration = last_entry["timestamp"] - first_entry["timestamp"]

        notes.append(f"Total timeline duration: ~{total_duration:.0f} seconds ({total_duration/60:.1f} minutes)")

        # Check for phase transitions
        phases = cactbot_data.get("phases", [])
        if len(phases) > 1:
            notes.append(f"Contains {len(phases)} phases")

        # Extract notable mechanics from guide
        guides = guide_data.get("guides", {})
        icyveins = guides.get("icy-veins", {})

        if icyveins.get("success"):
            content = icyveins.get("content", {})
            overview = content.get("overview", "")
            if overview:
                # Extract first few sentences
                sentences = overview.split(".")
                if sentences:
                    notes.append(f"Overview: {sentences[0][:200]}...")

        # Add common notes based on mechanics
        ability_names = [e["ability_name"] for e in entries]
        if any("Ultima" in name for name in ability_names):
            notes.append("Contains Ultima/Enrage cast - plan for DPS check")
        if any("Tank" in name or "Buster" in name for name in ability_names):
            notes.append("Contains tank busters - coordinate cooldowns")

        return notes

    def _calculate_confidence(
        self,
        cactbot_data: dict[str, Any],
        guide_data: dict[str, Any],
    ) -> float:
        """Calculate confidence score based on available data."""
        confidence = 0.0

        # Base confidence from cactbot data
        if cactbot_data.get("entries"):
            confidence += 0.5
        if cactbot_data.get("phases"):
            confidence += 0.2

        # Bonus from guide data
        guides = guide_data.get("guides", {})
        for source, data in guides.items():
            if data.get("success"):
                confidence += 0.15

        return min(confidence, 1.0)

    def _get_guide_sources(self, guide_data: dict[str, Any]) -> list[str]:
        """Get list of successful guide sources."""
        sources = []
        guides = guide_data.get("guides", {})

        for source, data in guides.items():
            if data.get("success"):
                sources.append(source)

        return sources

    def generate_cactbot_export(
        self,
        synthesized_data: dict[str, Any],
    ) -> str:
        """
        Generate cactbot-compatible timeline text.

        Args:
            synthesized_data: Synthesized timeline data

        Returns:
            Cactbot-compatible timeline text
        """
        lines = []

        boss_name = synthesized_data.get("boss_name", "Unknown")
        expansion = synthesized_data.get("expansion", "")
        encounter_type = synthesized_data.get("encounter_type", "")

        # Header
        lines.append(f"### {boss_name}")
        lines.append(f"### Expansion: {expansion}, Type: {encounter_type}")
        lines.append("")
        lines.append('hideall "--Reset--"')
        lines.append('hideall "--sync--"')
        lines.append("")
        lines.append('0.0 "--Reset--" ActorControl { command: "4000000F" } window 0,100000 jump 0')
        lines.append("")
        lines.append('0.0 "--sync--" InCombat { inGameCombat: "1" } window 0,1')
        lines.append("")

        # Add entries grouped by phase
        phases = synthesized_data.get("phases", [])
        for phase in phases:
            phase_name = phase.get("name", "Unknown")
            lines.append(f"### {phase_name}")
            lines.append("")

            abilities = phase.get("abilities", [])
            for ability in abilities:
                timestamp = ability.get("timestamp", 0)
                ability_name = ability.get("ability_name", "")
                ability_id = ability.get("ability_id")
                source = ability.get("source", "")

                # Build the entry line
                if ability_id and source:
                    line = f'{timestamp} "{ability_name}" Ability {{ id: "{ability_id}", source: "{source}" }}'
                elif ability_id:
                    line = f'{timestamp} "{ability_name}" Ability {{ id: "{ability_id}" }}'
                else:
                    line = f'{timestamp} "{ability_name}"'

                lines.append(line)

            lines.append("")

        # Add variations as comments
        variations = synthesized_data.get("variations", [])
        if variations:
            lines.append("### Variations")
            for variation in variations:
                lines.append(f"# {variation.get('title', '')}: {variation.get('description', '')}")
            lines.append("")

        # Add notes as comments
        notes = synthesized_data.get("notes", [])
        if notes:
            lines.append("### Notes")
            for note in notes:
                lines.append(f"# {note}")
            lines.append("")

        return "\n".join(lines)
