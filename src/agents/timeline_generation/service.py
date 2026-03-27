"""Atomic agent orchestration for encounter timeline generation."""

from __future__ import annotations

import json
from typing import Any

from fflogs_damage_timeline.postprocess import (
    SUPPORTED_CLASSIFICATIONS,
    build_generated_timeline_event_for_threshold,
    build_time_clusters,
)

from .models import EncounterTimeline, EncounterTimelineEvidence, TimelineCandidateSlot

TIMELINE_SELECTION_SYSTEM_PROMPT = """
You select the canonical unavoidable damage timeline for a Final Fantasy XIV boss encounter.
Return JSON only with this shape:
{
  "selected_slot_ids": ["slot-0001", "slot-0002"]
}
Rules:
- Select from the provided candidate slots only.
- Keep slot ids in strictly increasing timestamp order.
- Never invent slot ids, abilities, timestamps, classifications, modifiers, or damage values.
- Build one canonical encounter timeline from the pooled aligned fight evidence.
- Include only unavoidable boss damage. Exclude dodgeable mechanics and sparse outlier noise.
- Allowed classifications are raidwide, tankbuster, dual_tankbuster, and small_party.
- is_dot and is_multi_hit are modifiers, not classifications.
- stable, variable, and combined event kinds are all valid when supported by the evidence.
- Prefer candidates with broader distinct-report support when nearby or conflicting candidates overlap.
""".strip()


class TimelineGenerationError(RuntimeError):
    """Raised when atomic encounter timeline generation cannot be completed."""


def build_evidence_catalog(
    aligned_reports: list[dict[str, Any]],
    encounter_config: dict[str, Any] | None = None,
) -> EncounterTimelineEvidence:
    rows: list[dict[str, Any]] = []
    encounter_code = str((encounter_config or {}).get("code") or "")

    for report in aligned_reports:
        encounter_code = encounter_code or str((report.get("encounter") or {}).get("code") or "")
        report_code = str((report.get("report") or {}).get("code") or "")
        for fight in report.get("fights") or []:
            if not (fight.get("damage_events") or []):
                continue
            fight_index = _coerce_int(fight.get("fight_index"))
            fight_id = _coerce_int(fight.get("fight_id"))
            sample_key = f"{report_code}:{fight_index if fight_index is not None else 'unknown'}:{fight_id if fight_id is not None else len(rows)}"
            rows.append(
                {
                    "report_code": report_code,
                    "fight": fight,
                    "sample_key": sample_key,
                }
            )

    report_codes = sorted({str(row.get("report_code") or "") for row in rows if row.get("report_code")})
    source_fight_indexes = sorted(
        {
            int(row["fight"]["fight_index"])
            for row in rows
            if isinstance((row.get("fight") or {}).get("fight_index"), (int, float))
        }
    )
    report_count = len(report_codes)
    aligned_fight_count = len(rows)
    candidates: list[TimelineCandidateSlot] = []

    for cluster_index, cluster in enumerate(build_time_clusters(rows)):
        event = build_generated_timeline_event_for_threshold(
            cluster,
            branch_size=report_count,
            minimum_presence_ratio=0.0,
        )
        if event is None:
            continue

        relevant_windows = _relevant_cluster_windows(cluster, event)
        support_report_codes = sorted(
            {
                str(window.get("report_code") or "")
                for window in relevant_windows
                if window.get("report_code")
            }
        )
        support_fight_indexes = sorted(
            {
                int(window["fight_index"])
                for window in relevant_windows
                if isinstance(window.get("fight_index"), (int, float))
            }
        )
        support_fight_keys = {
            str(window.get("sample_key") or "")
            for window in relevant_windows
            if window.get("sample_key") is not None
        }
        candidates.append(
            TimelineCandidateSlot(
                slot_id=f"slot-{cluster_index:04d}",
                event=event,
                support_report_count=len(support_report_codes),
                support_fight_count=len(support_fight_keys) if support_fight_keys else len(relevant_windows),
                support_fight_indexes=support_fight_indexes,
                support_report_codes=support_report_codes,
                evidence_summary=_build_evidence_summary(
                    event=event,
                    support_report_count=len(support_report_codes),
                    report_count=report_count,
                    support_fight_count=len(support_fight_keys) if support_fight_keys else len(relevant_windows),
                    support_fight_indexes=support_fight_indexes,
                ),
            )
        )

    candidates.sort(key=lambda candidate: (candidate.timestamp_ms, candidate.slot_id))
    return EncounterTimelineEvidence(
        encounter_code=encounter_code,
        report_codes=report_codes,
        report_count=report_count,
        aligned_fight_count=aligned_fight_count,
        source_fight_indexes=source_fight_indexes,
        candidates=candidates,
    )


class TimelineGenerationService:
    def __init__(self, *, llm_client: Any):
        self.llm_client = llm_client

    def generate_encounter_timeline(
        self,
        aligned_reports: list[dict[str, Any]],
        encounter_config: dict[str, Any],
    ) -> dict[str, Any]:
        evidence = build_evidence_catalog(aligned_reports, encounter_config)
        if not evidence.candidates:
            return EncounterTimeline(
                encounter_code=evidence.encounter_code,
                report_codes=evidence.report_codes,
                report_count=evidence.report_count,
                aligned_fight_count=evidence.aligned_fight_count,
                source_fight_indexes=evidence.source_fight_indexes,
                events=[],
            ).to_dict()

        payload = self.llm_client.chat_json(
            TIMELINE_SELECTION_SYSTEM_PROMPT,
            self._build_prompt(evidence, encounter_config),
            temperature=0.0,
            max_retries=3,
        )
        selected_ids = self._validate_selection_payload(payload, evidence.candidates)
        selected_events = [
            self._validate_event(candidate.to_event_dict())
            for candidate in self._resolve_candidates(selected_ids, evidence.candidates)
        ]
        return EncounterTimeline(
            encounter_code=evidence.encounter_code,
            report_codes=evidence.report_codes,
            report_count=evidence.report_count,
            aligned_fight_count=evidence.aligned_fight_count,
            source_fight_indexes=evidence.source_fight_indexes,
            events=selected_events,
        ).to_dict()

    @staticmethod
    def _build_prompt(
        evidence: EncounterTimelineEvidence,
        encounter_config: dict[str, Any],
    ) -> str:
        payload = {
            "encounter": {
                "encounter_code": evidence.encounter_code,
                "full_name": encounter_config.get("full_name"),
                "boss_name": encounter_config.get("boss_name"),
                "report_count": evidence.report_count,
                "aligned_fight_count": evidence.aligned_fight_count,
                "source_fight_indexes": evidence.source_fight_indexes,
            },
            "candidate_slots": [
                candidate.to_prompt_dict(
                    total_report_count=evidence.report_count,
                    total_fight_count=evidence.aligned_fight_count,
                )
                for candidate in evidence.candidates
            ],
        }
        return json.dumps(payload, separators=(",", ":"))

    @staticmethod
    def _validate_selection_payload(
        payload: dict[str, Any],
        candidates: list[TimelineCandidateSlot],
    ) -> list[str]:
        selected_slot_ids = payload.get("selected_slot_ids")
        if not isinstance(selected_slot_ids, list):
            raise TimelineGenerationError("Atomic timeline agent must return a selected_slot_ids list")

        normalized_ids = [str(slot_id) for slot_id in selected_slot_ids]
        if len(normalized_ids) != len(set(normalized_ids)):
            raise TimelineGenerationError("Atomic timeline agent returned duplicate slot ids")

        candidate_ids = {candidate.slot_id for candidate in candidates}
        unknown_ids = [slot_id for slot_id in normalized_ids if slot_id not in candidate_ids]
        if unknown_ids:
            raise TimelineGenerationError(
                f"Atomic timeline agent returned unknown slot ids: {', '.join(unknown_ids)}"
            )
        return normalized_ids

    @staticmethod
    def _resolve_candidates(
        selected_ids: list[str],
        candidates: list[TimelineCandidateSlot],
    ) -> list[TimelineCandidateSlot]:
        candidates_by_id = {candidate.slot_id: candidate for candidate in candidates}
        selected_candidates = [candidates_by_id[slot_id] for slot_id in selected_ids]

        last_timestamp_ms: int | None = None
        for candidate in selected_candidates:
            if last_timestamp_ms is not None and candidate.timestamp_ms <= last_timestamp_ms:
                raise TimelineGenerationError(
                    "Atomic timeline agent must return slot ids in strictly increasing timestamp order"
                )
            last_timestamp_ms = candidate.timestamp_ms
        return selected_candidates

    @staticmethod
    def _validate_event(event: dict[str, Any]) -> dict[str, Any]:
        event_kind = str(event.get("event_kind") or "")
        if event_kind not in {"stable", "variable", "combined"}:
            raise TimelineGenerationError(f"Unsupported event kind returned from candidate rehydration: {event_kind}")

        classifications = event.get("classification")
        if isinstance(classifications, list):
            invalid = [
                str(value)
                for value in classifications
                if value is not None and str(value) not in SUPPORTED_CLASSIFICATIONS
            ]
            if invalid:
                raise TimelineGenerationError(
                    f"Encounter timeline event contains unsupported classifications: {', '.join(invalid)}"
                )
        elif classifications is not None and str(classifications) not in SUPPORTED_CLASSIFICATIONS:
            raise TimelineGenerationError(
                f"Encounter timeline event contains unsupported classification: {classifications}"
            )

        ability_names = event.get("ability_names") or []
        if ability_names:
            for field_name in (
                "classification",
                "is_dot",
                "is_multi_hit",
                "unmitigated_damage",
                "ability_type",
                "duration_ms",
            ):
                value = event.get(field_name)
                if isinstance(value, list) and len(value) != len(ability_names):
                    raise TimelineGenerationError(
                        f"Encounter timeline event field {field_name} must align with ability_names"
                    )
        return event


def _relevant_cluster_windows(
    cluster: dict[str, Any],
    event: dict[str, Any],
) -> list[dict[str, Any]]:
    retained_ability_names = set(_event_ability_names(event))
    relevant_windows = [
        dict(window)
        for window in cluster.get("windows") or []
        if retained_ability_names & set(window.get("ability_names") or [])
    ]
    return relevant_windows or [dict(window) for window in cluster.get("windows") or []]


def _event_ability_names(event: dict[str, Any]) -> list[str]:
    if event.get("ability_name"):
        return [str(event["ability_name"])]
    return [str(name) for name in event.get("ability_names") or []]


def _build_evidence_summary(
    *,
    event: dict[str, Any],
    support_report_count: int,
    report_count: int,
    support_fight_count: int,
    support_fight_indexes: list[int],
) -> str:
    ability_label = " / ".join(_event_ability_names(event)) or "unknown action"
    classification = _stringify_value(event.get("classification"))
    return (
        f"{ability_label} at {event.get('timestamp')} [{classification}] "
        f"supported by {support_report_count}/{report_count} reports and "
        f"{support_fight_count} fight samples across fight indexes {support_fight_indexes}."
    )


def _stringify_value(value: Any) -> str:
    if isinstance(value, list):
        return " / ".join(str(item) for item in value if item is not None) or "unknown"
    if value is None:
        return "unknown"
    return str(value)


def _coerce_int(value: Any) -> int | None:
    if not isinstance(value, (int, float)):
        return None
    return int(value)
