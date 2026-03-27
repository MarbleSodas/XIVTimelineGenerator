"""Atomic agents for encounter research, enrichment, and timeline generation."""

from typing import Any

from .encounter_research import EncounterResearchService
from .timeline_generation import TimelineGenerationService


def process_reports(
    aligned_reports: list[dict[str, Any]],
    encounter_config: dict[str, Any],
    llm_client: Any,
) -> dict[str, Any]:
    """Generate one atomic encounter timeline from aligned report evidence."""
    service = TimelineGenerationService(llm_client=llm_client)
    return service.generate_encounter_timeline(aligned_reports, encounter_config)


__all__ = ["EncounterResearchService", "TimelineGenerationService", "process_reports"]
