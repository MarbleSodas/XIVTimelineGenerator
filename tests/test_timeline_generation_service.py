import json

import pytest

from agents.timeline_generation.service import (
    TimelineGenerationError,
    TimelineGenerationService,
    build_evidence_catalog,
)

PARTY_TARGETS = [
    (101, "Warrior", "Tank One"),
    (102, "Paladin", "Tank Two"),
    (103, "Dancer", "DPS One"),
    (104, "Monk", "DPS Two"),
    (105, "Scholar", "Healer One"),
    (106, "WhiteMage", "Healer Two"),
    (107, "Pictomancer", "DPS Three"),
    (108, "Reaper", "DPS Four"),
]


def make_party_events(
    *,
    timestamp_ms: int,
    ability_name: str,
    target_count: int,
    damage: int,
    ability_type: str = "physical",
    is_dot: bool = False,
    multiplier: float | None = None,
    target_offset_ms: int = 20,
) -> list[dict]:
    events: list[dict] = []
    for index, (target_id, target_subtype, target_name) in enumerate(PARTY_TARGETS[:target_count]):
        event_timestamp_ms = timestamp_ms + (index * target_offset_ms)
        seconds = event_timestamp_ms // 1000
        milliseconds = event_timestamp_ms % 1000
        events.append(
            {
                "timestamp": f"00:{seconds:02d}.{milliseconds:03d}",
                "timestamp_ms": event_timestamp_ms,
                "ability_name": ability_name,
                "unmitigated_damage": damage,
                "ability_type": ability_type,
                "hit_type": "landed",
                "target_id": target_id,
                "target_subtype": target_subtype,
                "target_name": target_name,
                "is_dot": is_dot,
                "multiplier": multiplier,
            }
        )
    return events


def make_single_target_event(
    *,
    timestamp_ms: int,
    ability_name: str,
    damage: int,
    target_id: int = 999,
    target_subtype: str = "Monk",
    target_name: str = "DPS Two",
) -> list[dict]:
    seconds = timestamp_ms // 1000
    milliseconds = timestamp_ms % 1000
    return [
        {
            "timestamp": f"00:{seconds:02d}.{milliseconds:03d}",
            "timestamp_ms": timestamp_ms,
            "ability_name": ability_name,
            "unmitigated_damage": damage,
            "ability_type": "physical",
            "hit_type": "landed",
            "target_id": target_id,
            "target_subtype": target_subtype,
            "target_name": target_name,
            "is_dot": False,
            "multiplier": 1.0,
        }
    ]


def make_fight(
    fight_index: int,
    events: list[dict],
    *,
    fight_id: int | None = None,
    party_size: int = 8,
) -> dict:
    return {
        "fight_index": fight_index,
        "fight_id": fight_id if fight_id is not None else (fight_index + 1),
        "fight_name": "The Tyrant",
        "party_size": party_size,
        "damage_events": events,
    }


def make_aligned_report(report_code: str, fights: list[dict]) -> dict:
    return {
        "encounter": {"code": "M11S"},
        "report": {"code": report_code},
        "fights": fights,
    }


class FakeMiniMaxClient:
    def __init__(self, response_factory):
        self.response_factory = response_factory
        self.calls = []

    def chat_json(self, system_prompt, user_prompt, **kwargs):
        payload = json.loads(user_prompt)
        self.calls.append(payload)
        return self.response_factory(payload)


def test_build_evidence_catalog_pools_all_fight_indexes_and_tracks_support_metadata():
    aligned_reports = [
        make_aligned_report(
            "R1",
            [
                make_fight(
                    0,
                    make_party_events(
                        timestamp_ms=10_000,
                        ability_name="Crown of Arcadia",
                        target_count=8,
                        damage=100_000,
                        multiplier=0.5,
                    ),
                    fight_id=11,
                ),
                make_fight(
                    1,
                    make_party_events(
                        timestamp_ms=10_020,
                        ability_name="Crown of Arcadia",
                        target_count=8,
                        damage=95_000,
                        multiplier=0.5,
                    ),
                    fight_id=12,
                ),
            ],
        ),
        make_aligned_report(
            "R2",
            [
                make_fight(
                    0,
                    make_party_events(
                        timestamp_ms=9_980,
                        ability_name="Crown of Arcadia",
                        target_count=8,
                        damage=210_000,
                        multiplier=1.0,
                    ),
                    fight_id=21,
                )
            ],
        ),
    ]

    evidence = build_evidence_catalog(aligned_reports, {"code": "M11S"})

    assert evidence.encounter_code == "M11S"
    assert evidence.report_codes == ["R1", "R2"]
    assert evidence.report_count == 2
    assert evidence.aligned_fight_count == 3
    assert evidence.source_fight_indexes == [0, 1]
    assert len(evidence.candidates) == 1

    candidate = evidence.candidates[0]
    assert candidate.event["ability_name"] == "Crown of Arcadia"
    assert candidate.event["classification"] == "raidwide"
    assert candidate.event["unmitigated_damage"] == 200_000
    assert candidate.support_report_count == 2
    assert candidate.support_fight_count == 3
    assert candidate.support_fight_indexes == [0, 1]


def test_build_evidence_catalog_uses_distinct_reports_as_consensus_weight():
    aligned_reports = [
        make_aligned_report(
            "R1",
            [
                make_fight(0, make_party_events(timestamp_ms=12_000, ability_name="Impact", target_count=8, damage=180_000), fight_id=11),
                make_fight(1, make_party_events(timestamp_ms=12_010, ability_name="Impact", target_count=8, damage=182_000), fight_id=12),
            ],
        ),
        make_aligned_report(
            "R2",
            [
                make_fight(0, make_single_target_event(timestamp_ms=20_000, ability_name="Needle", damage=40_000), fight_id=21)
            ],
        ),
    ]

    evidence = build_evidence_catalog(aligned_reports, {"code": "M11S"})

    impact_candidate = next(
        candidate
        for candidate in evidence.candidates
        if candidate.event.get("ability_name") == "Impact"
    )
    assert impact_candidate.support_report_count == 1
    assert impact_candidate.support_fight_count == 2
    assert impact_candidate.support_fight_indexes == [0, 1]


def test_build_evidence_catalog_excludes_unsupported_candidates_before_agent():
    aligned_reports = [
        make_aligned_report(
            "R1",
            [make_fight(0, make_party_events(timestamp_ms=15_000, ability_name="Awkward Clip", target_count=3, damage=60_000), fight_id=11)],
        ),
        make_aligned_report(
            "R2",
            [make_fight(0, make_party_events(timestamp_ms=15_010, ability_name="Awkward Clip", target_count=3, damage=62_000), fight_id=21)],
        ),
    ]

    evidence = build_evidence_catalog(aligned_reports, {"code": "M11S"})

    assert evidence.candidates == []


def test_service_generates_variable_and_combined_encounter_events():
    aligned_reports = [
        make_aligned_report(
            "R1",
            [
                make_fight(
                    0,
                    make_party_events(timestamp_ms=10_000, ability_name="Heavy Hitter", target_count=8, damage=180_000)
                    + make_party_events(timestamp_ms=20_000, ability_name="Crush", target_count=8, damage=150_000)
                    + make_party_events(timestamp_ms=20_120, ability_name="Blast", target_count=8, damage=155_000),
                    fight_id=11,
                )
            ],
        ),
        make_aligned_report(
            "R2",
            [
                make_fight(
                    0,
                    make_party_events(timestamp_ms=10_020, ability_name="Impact", target_count=8, damage=182_000)
                    + make_party_events(timestamp_ms=20_010, ability_name="Crush", target_count=8, damage=152_000)
                    + make_party_events(timestamp_ms=20_130, ability_name="Blast", target_count=8, damage=157_000),
                    fight_id=21,
                )
            ],
        ),
    ]

    def response_factory(prompt_payload):
        selected_ids = []
        for candidate in prompt_payload["candidate_slots"]:
            if candidate["event_kind"] in {"variable", "combined"}:
                selected_ids.append(candidate["slot_id"])
        return {"selected_slot_ids": selected_ids}

    service = TimelineGenerationService(llm_client=FakeMiniMaxClient(response_factory))

    timeline = service.generate_encounter_timeline(
        aligned_reports,
        {"code": "M11S", "boss_name": "The Tyrant", "full_name": "AAC Heavyweight M3 (Savage)"},
    )

    assert timeline["encounter_code"] == "M11S"
    assert timeline["report_codes"] == ["R1", "R2"]
    assert timeline["report_count"] == 2
    assert timeline["aligned_fight_count"] == 2
    assert timeline["source_fight_indexes"] == [0]
    assert [event["event_kind"] for event in timeline["events"]] == ["variable", "combined"]
    assert timeline["events"][0]["ability_names"] == ["Heavy Hitter", "Impact"]
    assert timeline["events"][0]["support_report_count"] == 2
    assert timeline["events"][0]["support_fight_count"] == 2
    assert timeline["events"][1]["ability_names"] == ["Blast", "Crush"]
    assert timeline["events"][1]["support_report_count"] == 2


def test_service_rejects_invalid_payload_shape():
    aligned_reports = [
        make_aligned_report(
            "R1",
            [make_fight(0, make_party_events(timestamp_ms=10_000, ability_name="Crown of Arcadia", target_count=8, damage=180_000), fight_id=11)],
        )
    ]
    service = TimelineGenerationService(
        llm_client=FakeMiniMaxClient(lambda payload: {"selected_slot_ids": "slot-0000"})
    )

    with pytest.raises(TimelineGenerationError, match="selected_slot_ids list"):
        service.generate_encounter_timeline(aligned_reports, {"code": "M11S"})


def test_service_rejects_unknown_slot_ids():
    aligned_reports = [
        make_aligned_report(
            "R1",
            [make_fight(0, make_party_events(timestamp_ms=10_000, ability_name="Crown of Arcadia", target_count=8, damage=180_000), fight_id=11)],
        )
    ]
    service = TimelineGenerationService(
        llm_client=FakeMiniMaxClient(lambda payload: {"selected_slot_ids": ["slot-9999"]})
    )

    with pytest.raises(TimelineGenerationError, match="unknown slot ids"):
        service.generate_encounter_timeline(aligned_reports, {"code": "M11S"})


def test_service_rejects_duplicate_slot_ids():
    aligned_reports = [
        make_aligned_report(
            "R1",
            [make_fight(0, make_party_events(timestamp_ms=10_000, ability_name="Crown of Arcadia", target_count=8, damage=180_000), fight_id=11)],
        )
    ]

    def response_factory(prompt_payload):
        slot_id = prompt_payload["candidate_slots"][0]["slot_id"]
        return {"selected_slot_ids": [slot_id, slot_id]}

    service = TimelineGenerationService(llm_client=FakeMiniMaxClient(response_factory))

    with pytest.raises(TimelineGenerationError, match="duplicate slot ids"):
        service.generate_encounter_timeline(aligned_reports, {"code": "M11S"})


def test_service_rejects_unsorted_slot_ids():
    aligned_reports = [
        make_aligned_report(
            "R1",
            [
                make_fight(
                    0,
                    make_party_events(timestamp_ms=10_000, ability_name="Crown of Arcadia", target_count=8, damage=180_000)
                    + make_party_events(timestamp_ms=25_000, ability_name="Impact", target_count=8, damage=170_000),
                    fight_id=11,
                )
            ],
        )
    ]

    def response_factory(prompt_payload):
        slot_ids = [candidate["slot_id"] for candidate in prompt_payload["candidate_slots"]]
        return {"selected_slot_ids": list(reversed(slot_ids))}

    service = TimelineGenerationService(llm_client=FakeMiniMaxClient(response_factory))

    with pytest.raises(TimelineGenerationError, match="strictly increasing timestamp order"):
        service.generate_encounter_timeline(aligned_reports, {"code": "M11S"})
