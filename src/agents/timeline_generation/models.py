"""Typed models for atomic encounter timeline generation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TimelineCandidateSlot:
    slot_id: str
    event: dict[str, Any]
    support_report_count: int
    support_fight_count: int
    support_fight_indexes: list[int] = field(default_factory=list)
    support_report_codes: list[str] = field(default_factory=list)
    evidence_summary: str = ""

    @property
    def timestamp_ms(self) -> int:
        return int(self.event.get("timestamp_ms") or 0)

    def to_event_dict(self) -> dict[str, Any]:
        payload = deepcopy(self.event)
        payload["support_report_count"] = int(self.support_report_count)
        payload["support_fight_count"] = int(self.support_fight_count)
        payload["support_fight_indexes"] = list(self.support_fight_indexes)
        return payload

    def to_prompt_dict(
        self,
        *,
        total_report_count: int,
        total_fight_count: int,
    ) -> dict[str, Any]:
        payload = {
            "slot_id": self.slot_id,
            "timestamp_ms": self.event.get("timestamp_ms"),
            "event_kind": self.event.get("event_kind"),
            "classification": deepcopy(self.event.get("classification")),
            "is_dot": deepcopy(self.event.get("is_dot")),
            "is_multi_hit": deepcopy(self.event.get("is_multi_hit")),
            "support_report_count": int(self.support_report_count),
            "support_fight_count": int(self.support_fight_count),
            "support_fight_indexes": list(self.support_fight_indexes),
        }
        if self.event.get("ability_name") is not None:
            payload["ability_name"] = self.event.get("ability_name")
        if self.event.get("ability_names") is not None:
            payload["ability_names"] = deepcopy(self.event.get("ability_names"))
        payload["support_report_ratio"] = round(
            (self.support_report_count / total_report_count) if total_report_count else 0.0,
            4,
        )
        payload["support_fight_ratio"] = round(
            (self.support_fight_count / total_fight_count) if total_fight_count else 0.0,
            4,
        )
        return payload


@dataclass(frozen=True)
class EncounterTimelineEvidence:
    encounter_code: str
    report_codes: list[str]
    report_count: int
    aligned_fight_count: int
    source_fight_indexes: list[int]
    candidates: list[TimelineCandidateSlot] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["candidates"] = [candidate.to_event_dict() for candidate in self.candidates]
        return payload


@dataclass(frozen=True)
class EncounterTimeline:
    encounter_code: str
    report_codes: list[str]
    report_count: int
    aligned_fight_count: int
    source_fight_indexes: list[int]
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "encounter_code": self.encounter_code,
            "report_codes": list(self.report_codes),
            "report_count": int(self.report_count),
            "aligned_fight_count": int(self.aligned_fight_count),
            "source_fight_indexes": list(self.source_fight_indexes),
            "events": [deepcopy(event) for event in self.events],
        }
