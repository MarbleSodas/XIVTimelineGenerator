"""Timeline synthesizer — merges cactbot data with guide information."""

from datetime import datetime
from typing import Any


class TimelineSynthesizer:
    """Produces an enriched timeline from cactbot data and guide content."""

    def synthesize(
        self,
        cactbot_data: dict[str, Any],
        guide_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Synthesize timeline data with guide information.

        Returns a simplified timeline dict with phases, notes, and confidence.
        """
        boss_name = cactbot_data["boss_name"]
        phases = cactbot_data.get("phases", [])

        enhanced_phases = self._build_phases(phases, guide_data)
        notes = self._generate_notes(cactbot_data, guide_data)
        confidence = self._calculate_confidence(cactbot_data, guide_data)

        return {
            "boss_name": boss_name,
            "expansion": cactbot_data.get("expansion"),
            "encounter_type": cactbot_data.get("encounter_type"),
            "difficulty": cactbot_data.get("difficulty"),
            "phases": enhanced_phases,
            "notes": notes,
            "confidence": confidence,
            "generated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Phase building
    # ------------------------------------------------------------------

    def _build_phases(
        self,
        phases: list[dict[str, Any]],
        guide_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build phase dicts with entries and guide-sourced tips."""
        result: list[dict[str, Any]] = []

        guide_phases = (
            guide_data
            .get("guides", {})
            .get("icy-veins", {})
            .get("content", {})
            .get("phases", [])
        )

        for phase in phases:
            phase_name = phase.get("name", f"Phase {len(result) + 1}")
            entries = phase.get("entries", [])
            entries = [e for e in entries if e.get("ability_name") != "--sync--"]

            if not entries:
                continue

            first_ts = entries[0]["timestamp"]
            last_ts = entries[-1]["timestamp"]

            # Match guide tips by phase name
            tips: list[str] = []
            for gp in guide_phases:
                if phase_name.lower() in gp.get("title", "").lower():
                    if gp.get("tips"):
                        tips.extend(gp["tips"])
                    elif gp.get("content"):
                        tips.append(gp["content"])

            result.append({
                "name": phase_name,
                "start_time": first_ts,
                "end_time": last_ts,
                "entries": entries,
                "tips": tips,
            })

        return result

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def _generate_notes(
        self,
        cactbot_data: dict[str, Any],
        guide_data: dict[str, Any],
    ) -> list[str]:
        """Generate useful notes about the timeline."""
        entries = cactbot_data.get("entries", [])
        if not entries:
            return ["No timeline entries found"]

        notes: list[str] = []

        total_duration = entries[-1]["timestamp"] - entries[0]["timestamp"]
        notes.append(
            f"Total timeline duration: ~{total_duration:.0f}s "
            f"({total_duration / 60:.1f} min)"
        )

        phases = cactbot_data.get("phases", [])
        if len(phases) > 1:
            notes.append(f"Contains {len(phases)} phases")

        # Pull overview from guide if available
        guide_content = (
            guide_data
            .get("guides", {})
            .get("icy-veins", {})
            .get("content", {})
        )
        overview = guide_content.get("overview", "")
        if overview:
            first_sentence = overview.split(".")[0][:200]
            notes.append(f"Overview: {first_sentence}...")

        return notes

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    def _calculate_confidence(
        self,
        cactbot_data: dict[str, Any],
        guide_data: dict[str, Any],
    ) -> float:
        """Score 0–1 based on data availability."""
        score = 0.0

        if cactbot_data.get("entries"):
            score += 0.5
        if cactbot_data.get("phases"):
            score += 0.2

        for _source, data in guide_data.get("guides", {}).items():
            if data.get("success"):
                score += 0.15

        return min(score, 1.0)

    # ------------------------------------------------------------------
    # Cactbot export
    # ------------------------------------------------------------------

    def generate_cactbot_export(self, synthesized: dict[str, Any]) -> str:
        """Generate cactbot-compatible timeline text from synthesized data."""
        lines: list[str] = []

        boss = synthesized.get("boss_name", "Unknown")
        expansion = synthesized.get("expansion", "")
        enc_type = synthesized.get("encounter_type", "")

        lines.append(f"### {boss}")
        lines.append(f"### Expansion: {expansion}, Type: {enc_type}")
        lines.append("")
        lines.append('hideall "--Reset--"')
        lines.append('hideall "--sync--"')
        lines.append("")
        lines.append(
            '0.0 "--Reset--" ActorControl { command: "4000000F" } '
            "window 0,100000 jump 0"
        )
        lines.append("")
        lines.append('0.0 "--sync--" InCombat { inGameCombat: "1" } window 0,1')
        lines.append("")

        for phase in synthesized.get("phases", []):
            lines.append(f"### {phase.get('name', 'Unknown')}")
            lines.append("")

            for ability in phase.get("entries", []):
                ts = ability.get("timestamp", 0)
                name = ability.get("ability_name", "")
                aid = ability.get("ability_id")
                source = ability.get("source")

                if aid and source:
                    base_line = f'{ts} "{name}" Ability {{ id: "{aid}", source: "{source}" }}'
                elif aid:
                    base_line = f'{ts} "{name}" Ability {{ id: "{aid}" }}'
                else:
                    base_line = f'{ts} "{name}"'
                    
                damage = ability.get("unmitigated_damage")
                if damage is not None:
                    # Include damage range if available
                    d_min = ability.get("damage_min")
                    d_max = ability.get("damage_max")
                    if d_min is not None and d_max is not None:
                        base_line += f" # ~{damage:,.0f} ({d_min:,.0f}-{d_max:,.0f})"
                    else:
                        base_line += f" # ~{damage:,.0f} unmitigated dmg"
                    
                    tags = []
                    if ability.get("ability_type"):
                        tags.append(ability.get("ability_type"))
                    if ability.get("is_dot"):
                        tags.append("DOT")
                    
                    if tags:
                        base_line += f" [{', '.join(tags)}]"
                    
                    # Add mitigation note if present
                    mit_note = ability.get("mitigation_note")
                    if mit_note:
                        base_line += f" | mit: {mit_note}"
                        
                lines.append(base_line)

            lines.append("")

        # Notes as comments
        for note in synthesized.get("notes", []):
            lines.append(f"# {note}")

        return "\n".join(lines)
