import json
import os
from pathlib import Path

import pytest

TEST_PARTY_TARGETS = [
    ("Warrior", "Tank One"),
    ("Paladin", "Tank Two"),
    ("Dancer", "DPS One"),
    ("Monk", "DPS Two"),
    ("Scholar", "Healer One"),
    ("WhiteMage", "Healer Two"),
    ("Pictomancer", "DPS Three"),
    ("Reaper", "DPS Four"),
]


def support_events(
    events: list[dict],
    *,
    target_subtype: str = "Warrior",
    target_name: str = "Tank One",
    ability_type: str = "physical",
    hit_type: str = "landed",
    unmitigated_damage: int = 100000,
    is_dot: bool = False,
) -> list[dict]:
    return [
        {
            "unmitigated_damage": unmitigated_damage,
            "ability_type": ability_type,
            "hit_type": hit_type,
            "target_subtype": target_subtype,
            "target_name": target_name,
            "is_dot": is_dot,
            **event,
        }
        for event in events
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
    for index, (target_subtype, target_name) in enumerate(TEST_PARTY_TARGETS[:target_count]):
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
                "target_subtype": target_subtype,
                "target_name": target_name,
                "is_dot": is_dot,
                "multiplier": multiplier,
            }
        )
    return events


def make_party_dot_run(
    *,
    start_timestamps_ms: list[int],
    ability_name: str,
    target_count: int,
    damage: int,
    ability_type: str = "magical",
    multiplier: float | None = 1.0,
) -> list[dict]:
    events: list[dict] = []
    for target_index, (target_subtype, target_name) in enumerate(TEST_PARTY_TARGETS[:target_count]):
        offset_ms = target_index * 20
        for timestamp_ms in start_timestamps_ms:
            event_timestamp_ms = timestamp_ms + offset_ms
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
                    "target_subtype": target_subtype,
                    "target_name": target_name,
                    "is_dot": True,
                    "multiplier": multiplier,
                }
            )
    return events


def test_encounter_loader_finds_m11s():
    """Integration: EncounterLoader can find M11S with correct data."""
    from fflogs.encounters import EncounterLoader

    loader = EncounterLoader(
        Path("/Users/eugene/Documents/Github/XIVTimelineGenerator/data/encounters")
    )
    enc = loader.get_by_code("M11S")
    assert enc is not None
    assert enc.code == "M11S"
    assert enc.boss_name == "The Tyrant"
    assert enc.zone_id == 73
    assert enc.expansion == "dawntrail"
    assert enc.category == "savage"


def test_encounter_loader_finds_fru():
    """Integration: EncounterLoader can find FRU."""
    from fflogs.encounters import EncounterLoader

    loader = EncounterLoader(
        Path("/Users/eugene/Documents/Github/XIVTimelineGenerator/data/encounters")
    )
    enc = loader.get_by_code("FRU")
    assert enc is not None
    assert enc.code == "FRU"
    assert enc.full_name == "Futures Rewritten (Ultimate)"
    assert enc.zone_id == 65
    assert enc.category == "ultimate"


def test_cache_roundtrip(tmp_path):
    """Integration: CacheManager saves and loads token + encounter IDs."""
    from fflogs.cache import CacheManager

    cm = CacheManager(cache_dir=tmp_path)
    cm.save_token("abc", 3600)
    assert cm.load_token() == "abc"
    ids = {"M11S": 999, "TOP": 888}
    cm.save_encounter_ids(ids)
    assert cm.load_encounter_ids() == ids


def test_cache_expired_token(tmp_path):
    """Integration: CacheManager treats expired tokens as absent."""
    import time

    from fflogs.cache import CacheManager

    cm = CacheManager(cache_dir=tmp_path)
    cm.save_token("expired_token", expires_in=1)
    time.sleep(1.1)
    assert cm.load_token() is None


def test_all_dawntrail_encounters_load():
    """Integration: All Dawntrail encounters load without error."""
    from fflogs.encounters import EncounterLoader

    loader = EncounterLoader(
        Path("/Users/eugene/Documents/Github/XIVTimelineGenerator/data/encounters")
    )
    encounters = loader.load_expansion("dawntrail")
    codes = [e.code for e in encounters]
    expected = [
        "M1S",
        "M2S",
        "M3S",
        "M4S",
        "M5S",
        "M6S",
        "M7S",
        "M8S",
        "M9S",
        "M10S",
        "M11S",
        "M12S",
        "FRU",
    ]
    for code in expected:
        assert code in codes, f"{code} not found in encounters"


def test_all_endwalker_encounters_load():
    """Integration: All Endwalker encounters load without error."""
    from fflogs.encounters import EncounterLoader

    loader = EncounterLoader(
        Path("/Users/eugene/Documents/Github/XIVTimelineGenerator/data/encounters")
    )
    encounters = loader.load_expansion("endwalker")
    codes = [e.code for e in encounters]
    expected = [
        "P1S",
        "P2S",
        "P3S",
        "P4S",
        "P5S",
        "P6S",
        "P7S",
        "P8S",
        "P9S",
        "P10S",
        "P11S",
        "P12S",
        "TOP",
        "DSR",
    ]
    for code in expected:
        assert code in codes, f"{code} not found in encounters"


class TestFilters:
    @pytest.fixture
    def mock_events(self):
        return [
            {
                "timestamp": 5000,
                "targetID": 1,
                "sourceID": 100,
                "abilityGameID": 46085,
                "hitType": 1,
                "amount": 5000,
                "type": "damage",
            },
            {
                "timestamp": 5500,
                "targetID": 2,
                "sourceID": 100,
                "abilityGameID": 46086,
                "hitType": 2,
                "amount": 3000,
                "type": "damage",
            },
            {
                "timestamp": 6000,
                "targetID": 1,
                "sourceID": 100,
                "abilityGameID": 46085,
                "hitType": 1,
                "amount": 5000,
                "type": "calculateddamage",
            },
            {
                "timestamp": 6100,
                "targetID": 1,
                "sourceID": 200,
                "abilityGameID": 46085,
                "hitType": 1,
                "amount": 5000,
                "type": "damage",
            },
            {
                "timestamp": 6200,
                "targetID": 1,
                "sourceID": 300,
                "abilityGameID": 46085,
                "hitType": 1,
                "amount": 5000,
                "type": "damage",
            },
        ]

    @pytest.fixture
    def mock_actors(self):
        return {
            1: {"id": 1, "name": "Tank", "subType": "Warrior", "type": "Player"},
            2: {"id": 2, "name": "Boss Add", "subType": "Boss", "type": "NPC"},
            100: {"id": 100, "name": "The Tyrant", "subType": "Boss", "type": "NPC"},
            200: {"id": 200, "name": "Player", "subType": "Dancer", "type": "Player"},
            300: {"id": 300, "name": "Pet", "subType": "Pet", "type": "NPC", "petOwner": 200},
        }

    def test_filter_keeps_player_targeted_damage(self, mock_events, mock_actors):
        from fflogs_damage_timeline.filters import filter_damage_events

        result = filter_damage_events(mock_events, mock_actors, friendly_player_ids=[1])
        assert len(result) == 2
        assert all(event["targetID"] == 1 for event in result)
        assert [event["type"] for event in result] == ["damage", "calculateddamage"]


class TestNormalizer:
    def test_format_timestamp(self):
        from fflogs_damage_timeline.normalizer import format_timestamp

        assert format_timestamp(0) == "00:00.000"
        assert format_timestamp(61580) == "01:01.580"

    def test_normalize_fight_timeline_structures_events(self):
        from fflogs_damage_timeline.normalizer import normalize_fight_timeline

        fight = {
            "id": 5,
            "name": "The Tyrant",
            "startTime": 5000,
            "endTime": 9000,
            "encounterID": 103,
            "difficulty": 101,
            "kill": True,
            "friendlyPlayers": [1],
        }
        actors = [
            {
                "id": 1,
                "gameID": 1000001,
                "name": "Tank",
                "server": "Gilgamesh",
                "petOwner": None,
                "subType": "Warrior",
                "type": "Player",
            },
            {
                "id": 100,
                "gameID": 19169,
                "name": "The Tyrant",
                "server": None,
                "petOwner": None,
                "subType": "Boss",
                "type": "NPC",
            },
        ]
        abilities = [
            {"gameID": 46085, "name": "Attack", "type": 1},
            {"gameID": 46086, "name": "Crown of Arcadia", "type": 1},
        ]
        events = [
            {
                "timestamp": 5000,
                "type": "calculateddamage",
                "packetID": 10,
                "sourceID": 100,
                "targetID": 1,
                "abilityGameID": 46085,
                "fight": 5,
                "buffs": "1000048.1000297.",
                "hitType": 1,
                "amount": 44600,
                "unmitigatedAmount": 44600,
                "multiplier": 1,
            },
            {
                "timestamp": 5531,
                "type": "damage",
                "packetID": 10,
                "sourceID": 100,
                "targetID": 1,
                "abilityGameID": 46085,
                "fight": 5,
                "buffs": "1000048.1000297.",
                "hitType": 1,
                "amount": 44600,
                "unmitigatedAmount": 68000,
                "absorbed": 23400,
                "multiplier": 1,
            },
            {
                "timestamp": 6123,
                "type": "damage",
                "packetID": 11,
                "sourceID": 100,
                "targetID": 1,
                "abilityGameID": 46086,
                "fight": 5,
                "buffs": "1001457.",
                "hitType": 1,
                "amount": 90000,
                "unmitigatedAmount": 120000,
                "multiplier": 0.75,
            },
        ]

        result = normalize_fight_timeline(
            fight=fight,
            report_start_time=1_000_000,
            events=events,
            actors=actors,
            abilities=abilities,
        )

        assert result["fight_id"] == 5
        assert result["duration_ms"] == 4000
        assert result["event_count"] == 1
        assert result["events"][0]["timestamp"] == "00:01.123"
        assert result["events"][0]["category"] == "damage"
        assert result["events"][0]["ability"]["name"] == "Crown of Arcadia"
        assert result["events"][0]["ability"]["is_auto_attack"] is False
        assert result["events"][0]["damage"]["reduction_amount"] == 30000
        assert result["events"][0]["damage"]["reduction_percent"] == 25.0
        assert result["events"][0]["buff_ids"] == [1001457]


class TestOutput:
    @pytest.fixture
    def report_timeline(self):
        return {
            "encounter": {"code": "M11S", "boss_name": "The Tyrant"},
            "report": {
                "code": "ABC123",
                "title": "AAC Heavyweight",
                "start_time_ms": 1000,
                "end_time_ms": 9000,
                "kill_fight_count": 1,
            },
            "fights": [
                {
                    "fight_id": 5,
                    "event_count": 2,
                    "events": [
                        {"timestamp": "00:00.000"},
                        {"timestamp": "00:00.531"},
                    ],
                }
            ],
        }

    def test_output_creates_correct_json_structure(self, tmp_path, report_timeline):
        from fflogs_damage_timeline.output import write_report_timeline

        result = write_report_timeline(tmp_path, "M11S", report_timeline)
        assert result.exists()

        with result.open() as file_handle:
            data = json.load(file_handle)

        assert data["report"]["code"] == "ABC123"
        assert data["report"]["kill_fight_count"] == 1
        assert len(data["fights"]) == 1
        assert data["fights"][0]["event_count"] == 2
        assert "postprocessed" not in data

    def test_output_overwrites_existing_report_file(self, tmp_path, report_timeline):
        from fflogs_damage_timeline.output import write_report_timeline

        result = write_report_timeline(tmp_path, "M11S", report_timeline)
        result.write_text("stale")

        write_report_timeline(tmp_path, "M11S", report_timeline)
        with result.open() as file_handle:
            data = json.load(file_handle)

        assert data["report"]["code"] == "ABC123"

    def test_postprocessed_output_writes_suffixed_file_in_stage_folder(self, tmp_path):
        from fflogs_damage_timeline.output import write_postprocessed_report

        postprocessed = {
            "encounter": {"code": "M11S"},
            "report": {"code": "ABC123"},
            "fights": [
                {
                    "fight_index": 0,
                    "damage_events": [
                        {"timestamp": "00:00.531", "ability_name": "Crown of Arcadia"}
                    ],
                }
            ],
        }

        result = write_postprocessed_report(
            tmp_path,
            "M11S",
            "ABC123",
            postprocessed,
        )

        assert result == tmp_path / "M11S" / "postprocessed" / "ABC123.postprocessed.json"
        with result.open() as file_handle:
            data = json.load(file_handle)
        assert data["fights"][0]["damage_events"][0]["ability_name"] == "Crown of Arcadia"
        assert "fields" not in data

    def test_aligned_postprocessed_output_writes_suffixed_file_in_stage_folder(self, tmp_path):
        from fflogs_damage_timeline.output import write_aligned_postprocessed_report

        aligned_report = {
            "encounter": {"code": "M11S"},
            "report": {"code": "ABC123"},
            "fights": [
                {
                    "fight_index": 0,
                    "damage_events": [{"timestamp": "00:01.000"}],
                }
            ],
        }

        result = write_aligned_postprocessed_report(
            tmp_path,
            "M11S",
            "ABC123",
            aligned_report,
        )

        assert result == tmp_path / "M11S" / "aligned" / "ABC123.aligned.json"
        with result.open() as file_handle:
            data = json.load(file_handle)
        assert data["fights"][0]["damage_events"][0]["timestamp"] == "00:01.000"
        assert "alignment_summary" not in data

    def test_generated_timeline_output_writes_suffixed_file_in_stage_folder(self, tmp_path):
        from fflogs_damage_timeline.output import write_generated_timeline

        generated_timeline = {
            "encounter_code": "M11S",
            "fight_index": 0,
            "branch_index": 1,
            "events": [
                {
                    "timestamp": "00:01.000",
                    "ability_name": "Crown of Arcadia",
                    "unmitigated_damage": 160000,
                    "ability_type": "physical",
                    "hit_type": "landed",
                    "target_subtype": "Sage",
                    "target_name": "Healer",
                    "is_dot": False,
                }
            ],
        }

        result = write_generated_timeline(
            tmp_path,
            "M11S",
            0,
            1,
            generated_timeline,
        )

        assert result == tmp_path / "M11S" / "generated" / "fight-0-branch-1.timeline.json"
        with result.open() as file_handle:
            data = json.load(file_handle)
        assert data["events"][0]["ability_name"] == "Crown of Arcadia"
        assert data["events"][0]["unmitigated_damage"] == 160000

    def test_encounter_timeline_output_writes_single_encounter_file(self, tmp_path):
        from fflogs_damage_timeline.output import write_encounter_timeline

        encounter_timeline = {
            "encounter_code": "M11S",
            "report_codes": ["R1", "R2"],
            "report_count": 2,
            "aligned_fight_count": 3,
            "source_fight_indexes": [0, 1],
            "events": [
                {
                    "timestamp": "00:12.250",
                    "timestamp_ms": 12250,
                    "event_kind": "stable",
                    "ability_name": "Crown of Arcadia",
                    "classification": "raidwide",
                    "is_dot": False,
                    "is_multi_hit": False,
                    "unmitigated_damage": 200000,
                    "ability_type": "physical",
                    "support_report_count": 2,
                    "support_fight_count": 3,
                    "support_fight_indexes": [0, 1],
                }
            ],
        }

        result = write_encounter_timeline(
            tmp_path,
            "M11S",
            encounter_timeline,
        )

        assert result == tmp_path / "M11S" / "generated" / "encounter.timeline.json"
        with result.open() as file_handle:
            data = json.load(file_handle)
        assert data["events"][0]["ability_name"] == "Crown of Arcadia"
        assert data["report_count"] == 2


def test_cli_builds_report_timeline():
    from fflogs_damage_timeline.cli import build_report_timeline

    encounter_config = {"code": "M11S", "boss_name": "The Tyrant"}
    report_details = {
        "code": "ABC123",
        "title": "AAC Heavyweight",
        "startTime": 1000,
        "endTime": 2000,
        "playerDetails": {
            "tanks": [
                {"name": "Tank One", "combatantInfo": {"hitPoints": 220000}},
                {"name": "Tank Two", "combatantInfo": {"hitPoints": 240000}},
            ],
            "healers": [
                {"name": "Healer One", "combatantInfo": {"maxHitPoints": 160000}},
                {"name": "Healer Two", "combatantInfo": {"maxHitPoints": 164000}},
            ],
        },
    }
    fight_timelines = [{"fight_id": 5}, {"fight_id": 6}]

    result = build_report_timeline(encounter_config, report_details, fight_timelines)
    assert result["report"]["code"] == "ABC123"
    assert result["report"]["kill_fight_count"] == 2
    assert result["report"]["minimum_tank_health"] == 220000
    assert result["report"]["minimum_healer_health"] == 160000
    assert [fight["fight_id"] for fight in result["fights"]] == [5, 6]


def test_cli_builds_report_timeline_with_missing_role_health():
    from fflogs_damage_timeline.cli import build_report_timeline

    encounter_config = {"code": "M11S", "boss_name": "The Tyrant"}
    report_details = {
        "code": "ABC123",
        "title": "AAC Heavyweight",
        "startTime": 1000,
        "endTime": 2000,
        "playerDetails": {
            "tanks": [{"name": "Tank One"}],
            "healers": [{"name": "Healer One", "combatantInfo": {"gear": []}}],
        },
    }

    result = build_report_timeline(encounter_config, report_details, [{"fight_id": 5}])

    assert result["report"]["minimum_tank_health"] is None
    assert result["report"]["minimum_healer_health"] is None


def test_postprocess_builds_cleaned_damage_events():
    from fflogs_damage_timeline.postprocess import build_postprocessed_report

    report_timeline = {
        "encounter": {"code": "M11S"},
        "report": {"code": "ABC123"},
        "fights": [
            {
                "fight_id": 5,
                "name": "The Tyrant",
                "events": [
                    {
                        "timestamp": "00:10.158",
                        "timestamp_ms": 10158,
                        "ability": {"name": "Crown of Arcadia", "type": "128"},
                        "damage": {"unmitigated_amount": 160000, "blocked": 0, "multiplier": 1},
                        "hit_type": 1,
                        "target": {"sub_type": "Sage", "name": "Healer"},
                        "tick": False,
                    }
                ],
            }
        ],
    }

    result = build_postprocessed_report(report_timeline)
    assert result["encounter"]["code"] == "M11S"
    assert result["report"]["code"] == "ABC123"
    assert result["fights"][0]["fight_index"] == 0
    assert result["fights"][0]["damage_events"][0]["ability_name"] == "Crown of Arcadia"
    assert result["fights"][0]["damage_events"][0]["ability_type"] == "physical"
    assert result["fights"][0]["damage_events"][0]["hit_type"] == "landed"
    assert result["fights"][0]["damage_events"][0]["is_dot"] is False
    assert result["fights"][0]["damage_events"][0]["multiplier"] == 1
    assert "fields" not in result


def test_postprocess_groups_multiple_fights_separately():
    from fflogs_damage_timeline.postprocess import build_postprocessed_report

    report_timeline = {
        "encounter": {"code": "M11S"},
        "report": {"code": "ABC123"},
        "fights": [
            {
                "fight_id": 5,
                "name": "The Tyrant",
                "events": [
                    {
                        "timestamp": "00:01.000",
                        "timestamp_ms": 1000,
                        "ability": {"name": "Hit One", "type": "128"},
                        "damage": {"unmitigated_amount": 1000, "blocked": 0},
                        "hit_type": 1,
                        "target": {"sub_type": "Warrior", "name": "Tank"},
                        "tick": False,
                    }
                ],
            },
            {
                "fight_id": 6,
                "name": "The Tyrant",
                "events": [
                    {
                        "timestamp": "00:02.000",
                        "timestamp_ms": 2000,
                        "ability": {"name": "Hit Two", "type": "1024"},
                        "damage": {"unmitigated_amount": 2000, "blocked": 0},
                        "hit_type": 1,
                        "target": {"sub_type": "Sage", "name": "Healer"},
                        "tick": False,
                    }
                ],
            },
        ],
    }

    result = build_postprocessed_report(report_timeline)
    assert [fight["fight_id"] for fight in result["fights"]] == [5, 6]
    assert result["fights"][0]["damage_events"][0]["ability_name"] == "Hit One"
    assert result["fights"][1]["damage_events"][0]["ability_name"] == "Hit Two"


def test_aligned_reports_use_median_first_event_per_fight_order():
    from fflogs_damage_timeline.postprocess import build_aligned_postprocessed_reports

    reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {"timestamp": "00:00.900", "timestamp_ms": 900},
                        {"timestamp": "00:01.100", "timestamp_ms": 1100},
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {"timestamp": "00:01.000", "timestamp_ms": 1000},
                        {"timestamp": "00:01.200", "timestamp_ms": 1200},
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R3"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {"timestamp": "00:01.300", "timestamp_ms": 1300},
                        {"timestamp": "00:01.500", "timestamp_ms": 1500},
                    ],
                }
            ],
        },
    ]

    aligned_reports = build_aligned_postprocessed_reports(reports)
    aligned_by_code = {report["report"]["code"]: report for report in aligned_reports}

    assert aligned_by_code["R1"]["fights"][0]["damage_events"][0]["timestamp_ms"] == 1000
    assert aligned_by_code["R3"]["fights"][0]["damage_events"][1]["timestamp_ms"] == 1200
    assert "alignment_summary" not in aligned_by_code["R1"]


def test_aligned_reports_skip_empty_fights_and_align_per_fight_order():
    from fflogs_damage_timeline.postprocess import build_aligned_postprocessed_reports

    reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "Fight 1",
                    "damage_events": [{"timestamp": "00:01.000", "timestamp_ms": 1000}],
                },
                {
                    "fight_index": 1,
                    "fight_id": 2,
                    "fight_name": "Fight 2",
                    "damage_events": [],
                },
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "Fight 1",
                    "damage_events": [{"timestamp": "00:01.100", "timestamp_ms": 1100}],
                },
                {
                    "fight_index": 1,
                    "fight_id": 4,
                    "fight_name": "Fight 2",
                    "damage_events": [{"timestamp": "00:03.000", "timestamp_ms": 3000}],
                },
            ],
        },
    ]

    aligned_reports = build_aligned_postprocessed_reports(reports)
    aligned_r1 = next(report for report in aligned_reports if report["report"]["code"] == "R1")
    aligned_r2 = next(report for report in aligned_reports if report["report"]["code"] == "R2")

    assert aligned_r1["fights"][0]["damage_events"][0]["timestamp_ms"] == 1050
    assert aligned_r1["fights"][1]["damage_events"] == []
    assert aligned_r2["fights"][1]["damage_events"][0]["timestamp_ms"] == 3000


def test_generated_timelines_build_stable_slots_from_aligned_reports():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.000",
                            "timestamp_ms": 1000,
                            "ability_name": "A",
                                "unmitigated_damage": 100000,
                                "ability_type": "physical",
                                "hit_type": "landed",
                                "target_subtype": "Warrior",
                                "target_name": "Tank One",
                                "is_dot": False,
                            },
                        {
                            "timestamp": "00:03.000",
                            "timestamp_ms": 3000,
                            "ability_name": "B",
                            "unmitigated_damage": 200000,
                            "ability_type": "magical",
                            "hit_type": "blocked",
                            "target_subtype": "Warrior",
                            "target_name": "Tank",
                            "is_dot": False,
                        },
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.100",
                            "timestamp_ms": 1100,
                            "ability_name": "A",
                                "unmitigated_damage": 100000,
                                "ability_type": "physical",
                                "hit_type": "landed",
                                "target_subtype": "Warrior",
                                "target_name": "Tank One",
                                "is_dot": False,
                            },
                        {
                            "timestamp": "00:03.100",
                            "timestamp_ms": 3100,
                            "ability_name": "B",
                            "unmitigated_damage": 200000,
                            "ability_type": "magical",
                            "hit_type": "blocked",
                            "target_subtype": "Warrior",
                            "target_name": "Tank",
                            "is_dot": False,
                        },
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R3"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:00.900",
                            "timestamp_ms": 900,
                            "ability_name": "A",
                            "unmitigated_damage": 100000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:03.050",
                            "timestamp_ms": 3050,
                            "ability_name": "B",
                            "unmitigated_damage": 200000,
                            "ability_type": "magical",
                            "hit_type": "blocked",
                            "target_subtype": "Warrior",
                            "target_name": "Tank",
                            "is_dot": False,
                        },
                    ],
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 1
    assert timelines[0]["encounter_code"] == "M11S"
    assert timelines[0]["fight_index"] == 0
    assert timelines[0]["branch_index"] == 0
    assert timelines[0]["events"][0]["event_kind"] == "stable"
    assert timelines[0]["events"][0]["ability_name"] == "A"
    assert timelines[0]["events"][0]["unmitigated_damage"] == 100000
    assert timelines[0]["events"][0]["ability_type"] == "physical"
    assert timelines[0]["events"][0]["is_dot"] is False
    assert timelines[0]["events"][0]["is_multi_hit"] is False
    assert timelines[0]["events"][0]["classification"] == "tankbuster"
    assert "hit_type" not in timelines[0]["events"][0]
    assert "target_subtype" not in timelines[0]["events"][0]
    assert "target_name" not in timelines[0]["events"][0]
    assert timelines[0]["events"][1]["ability_name"] == "B"
    assert timelines[0]["events"][1]["unmitigated_damage"] == 200000
    assert timelines[0]["events"][1]["classification"] == "tankbuster"


def test_generated_timelines_merge_same_time_variable_abilities():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.000",
                            "timestamp_ms": 1000,
                            "ability_name": "A",
                                "unmitigated_damage": 100000,
                                "ability_type": "physical",
                                "hit_type": "landed",
                                "target_subtype": "Warrior",
                                "target_name": "Tank One",
                                "is_dot": False,
                            },
                        {
                            "timestamp": "00:01.700",
                            "timestamp_ms": 1700,
                            "ability_name": "B",
                            "unmitigated_damage": 200000,
                            "ability_type": "magical",
                            "hit_type": "blocked",
                            "target_subtype": "Warrior",
                            "target_name": "Tank",
                            "is_dot": False,
                        },
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.100",
                            "timestamp_ms": 1100,
                            "ability_name": "B",
                            "unmitigated_damage": 200000,
                            "ability_type": "magical",
                            "hit_type": "blocked",
                            "target_subtype": "Warrior",
                            "target_name": "Tank",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.800",
                            "timestamp_ms": 1800,
                            "ability_name": "A",
                                "unmitigated_damage": 100000,
                                "ability_type": "physical",
                                "hit_type": "landed",
                                "target_subtype": "Warrior",
                                "target_name": "Tank One",
                                "is_dot": False,
                            },
                    ],
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 1
    assert len(timelines[0]["events"]) == 1
    assert timelines[0]["events"][0]["event_kind"] == "combined"
    assert timelines[0]["events"][0]["ability_names"] == ["A", "B"]
    assert timelines[0]["events"][0]["unmitigated_damage"] == [100000, 200000]
    assert timelines[0]["events"][0]["ability_type"] == ["physical", "magical"]
    assert timelines[0]["events"][0]["is_dot"] == [False, False]
    assert timelines[0]["events"][0]["is_multi_hit"] == [False, False]
    assert timelines[0]["events"][0]["classification"] == ["tankbuster", "tankbuster"]
    assert "hit_type" not in timelines[0]["events"][0]
    assert "target_subtype" not in timelines[0]["events"][0]
    assert "target_name" not in timelines[0]["events"][0]


def test_generated_timelines_keep_alternate_single_ability_slots_as_variable():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.000",
                            "timestamp_ms": 1000,
                            "ability_name": "A",
                                "unmitigated_damage": 100000,
                                "ability_type": "physical",
                                "hit_type": "landed",
                                "target_subtype": "Warrior",
                                "target_name": "Tank One",
                                "is_dot": False,
                            }
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.050",
                            "timestamp_ms": 1050,
                            "ability_name": "B",
                            "unmitigated_damage": 200000,
                            "ability_type": "magical",
                            "hit_type": "blocked",
                            "target_subtype": "Warrior",
                            "target_name": "Tank",
                            "is_dot": False,
                        }
                    ],
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 1
    assert len(timelines[0]["events"]) == 1
    assert timelines[0]["events"][0]["event_kind"] == "variable"
    assert timelines[0]["events"][0]["ability_names"] == ["A", "B"]


def test_generated_timelines_keep_variable_raidwides_with_partial_target_samples():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "party_size": 8,
                    "damage_events": make_party_events(
                        timestamp_ms=1000,
                        ability_name="Heavy Hitter",
                        target_count=5,
                        damage=100000,
                    ),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "party_size": 8,
                    "damage_events": make_party_events(
                        timestamp_ms=1050,
                        ability_name="Impact",
                        target_count=6,
                        damage=110000,
                    ),
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 1
    assert len(timelines[0]["events"]) == 1
    assert timelines[0]["events"][0]["event_kind"] == "variable"
    assert timelines[0]["events"][0]["ability_names"] == ["Heavy Hitter", "Impact"]
    assert timelines[0]["events"][0]["classification"] == ["raidwide", "raidwide"]
    assert timelines[0]["events"][0]["unmitigated_damage"] == [100000, 110000]


def test_generated_timelines_split_phase_skip_into_separate_branches():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "FULL1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "Start"},
                        {"timestamp": "00:05.000", "timestamp_ms": 5000, "ability_name": "Block A"},
                        {"timestamp": "00:09.000", "timestamp_ms": 9000, "ability_name": "Block B"},
                        {"timestamp": "00:13.000", "timestamp_ms": 13000, "ability_name": "End"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "FULL2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.100", "timestamp_ms": 1100, "ability_name": "Start"},
                        {"timestamp": "00:05.100", "timestamp_ms": 5100, "ability_name": "Block A"},
                        {"timestamp": "00:09.100", "timestamp_ms": 9100, "ability_name": "Block B"},
                        {"timestamp": "00:13.100", "timestamp_ms": 13100, "ability_name": "End"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "SKIP"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "Start"},
                        {"timestamp": "00:04.900", "timestamp_ms": 4900, "ability_name": "End"},
                    ]),
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 2
    branch_events = [timeline["events"] for timeline in sorted(timelines, key=lambda item: item["branch_index"])]
    assert any(len(events) >= 3 for events in branch_events)
    assert any(len(events) == 2 for events in branch_events)


def test_generated_timelines_keep_most_common_route_first_with_branch_metadata():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    dominant_route_one = support_events([
        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "Start"},
        {"timestamp": "00:05.000", "timestamp_ms": 5000, "ability_name": "Core A"},
        {"timestamp": "00:09.000", "timestamp_ms": 9000, "ability_name": "Core B"},
        {"timestamp": "00:13.000", "timestamp_ms": 13000, "ability_name": "End"},
    ])
    dominant_route_two = support_events([
        {"timestamp": "00:01.100", "timestamp_ms": 1100, "ability_name": "Start"},
        {"timestamp": "00:05.100", "timestamp_ms": 5100, "ability_name": "Core A"},
        {"timestamp": "00:09.100", "timestamp_ms": 9100, "ability_name": "Core B"},
        {"timestamp": "00:13.100", "timestamp_ms": 13100, "ability_name": "End"},
    ])
    minority_long_route = support_events([
        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "Start"},
        {"timestamp": "00:05.050", "timestamp_ms": 5050, "ability_name": "Alt A"},
        {"timestamp": "00:09.050", "timestamp_ms": 9050, "ability_name": "Alt B"},
        {"timestamp": "00:13.050", "timestamp_ms": 13050, "ability_name": "End"},
        {"timestamp": "00:17.050", "timestamp_ms": 17050, "ability_name": "Alt D"},
    ])

    aligned_reports = [
        {"encounter": {"code": "M11S"}, "report": {"code": "DOM1"}, "fights": [{"fight_index": 0, "damage_events": dominant_route_one}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "DOM2"}, "fights": [{"fight_index": 0, "damage_events": dominant_route_two}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "ALT1"}, "fights": [{"fight_index": 0, "damage_events": minority_long_route}]},
    ]

    timelines = sorted(build_generated_timelines(aligned_reports), key=lambda item: item["branch_index"])
    assert len(timelines) == 2

    primary_timeline = timelines[0]
    alternate_timeline = timelines[1]
    assert primary_timeline["branch_index"] == 0
    assert primary_timeline["is_primary_branch"] is True
    assert primary_timeline["sample_count"] == 2
    assert primary_timeline["sample_ratio"] == 0.6667
    assert primary_timeline["report_codes"] == ["DOM1", "DOM2"]
    assert primary_timeline["first_divergence_timestamp_ms"] is None
    assert [event.get("ability_name") for event in primary_timeline["events"]] == [
        "Start",
        "Core A",
        "Core B",
        "End",
    ]

    assert alternate_timeline["branch_index"] == 1
    assert alternate_timeline["is_primary_branch"] is False
    assert alternate_timeline["sample_count"] == 1
    assert alternate_timeline["sample_ratio"] == 0.3333
    assert alternate_timeline["report_codes"] == ["ALT1"]
    assert alternate_timeline["first_divergence_timestamp_ms"] == 5050
    assert alternate_timeline["first_divergence_timestamp"] == "00:05.050"


def test_generated_timelines_order_alternate_branches_by_sample_count():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    primary_route = support_events([
        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "Start"},
        {"timestamp": "00:05.000", "timestamp_ms": 5000, "ability_name": "Primary A"},
        {"timestamp": "00:09.000", "timestamp_ms": 9000, "ability_name": "Primary B"},
        {"timestamp": "00:13.000", "timestamp_ms": 13000, "ability_name": "End"},
    ])
    secondary_route = support_events([
        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "Start"},
        {"timestamp": "00:05.050", "timestamp_ms": 5050, "ability_name": "Secondary A"},
        {"timestamp": "00:09.050", "timestamp_ms": 9050, "ability_name": "Secondary B"},
        {"timestamp": "00:13.050", "timestamp_ms": 13050, "ability_name": "End"},
    ])
    tertiary_route = support_events([
        {"timestamp": "00:01.075", "timestamp_ms": 1075, "ability_name": "Start"},
        {"timestamp": "00:05.075", "timestamp_ms": 5075, "ability_name": "Tertiary A"},
        {"timestamp": "00:09.075", "timestamp_ms": 9075, "ability_name": "Tertiary B"},
        {"timestamp": "00:13.075", "timestamp_ms": 13075, "ability_name": "End"},
    ])

    aligned_reports = [
        {"encounter": {"code": "M11S"}, "report": {"code": "P1"}, "fights": [{"fight_index": 0, "damage_events": primary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "P2"}, "fights": [{"fight_index": 0, "damage_events": primary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "P3"}, "fights": [{"fight_index": 0, "damage_events": primary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "S1"}, "fights": [{"fight_index": 0, "damage_events": secondary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "S2"}, "fights": [{"fight_index": 0, "damage_events": secondary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "T1"}, "fights": [{"fight_index": 0, "damage_events": tertiary_route}]},
    ]

    timelines = sorted(build_generated_timelines(aligned_reports), key=lambda item: item["branch_index"])
    assert [timeline["sample_count"] for timeline in timelines] == [3, 2, 1]
    assert [timeline["report_codes"] for timeline in timelines] == [
        ["P1", "P2", "P3"],
        ["S1", "S2"],
        ["T1"],
    ]


def test_generated_timelines_fold_sub_fifteen_percent_outlier_without_losing_mainline_tail():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    primary_route = support_events([
        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "Start"},
        {"timestamp": "00:05.000", "timestamp_ms": 5000, "ability_name": "Middle"},
        {"timestamp": "00:09.000", "timestamp_ms": 9000, "ability_name": "End"},
    ])
    outlier_route = support_events([
        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "Start"},
        {"timestamp": "00:06.000", "timestamp_ms": 6000, "ability_name": "Branch"},
        {"timestamp": "00:11.000", "timestamp_ms": 11000, "ability_name": "Extra"},
    ])

    aligned_reports = [
        {"encounter": {"code": "M11S"}, "report": {"code": "P1"}, "fights": [{"fight_index": 0, "damage_events": primary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "P2"}, "fights": [{"fight_index": 0, "damage_events": primary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "P3"}, "fights": [{"fight_index": 0, "damage_events": primary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "P4"}, "fights": [{"fight_index": 0, "damage_events": primary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "P5"}, "fights": [{"fight_index": 0, "damage_events": primary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "P6"}, "fights": [{"fight_index": 0, "damage_events": primary_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "OUT"}, "fights": [{"fight_index": 0, "damage_events": outlier_route}]},
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 1
    assert timelines[0]["sample_count"] == 7
    assert timelines[0]["sample_ratio"] == 1.0
    assert [event.get("ability_name") for event in timelines[0]["events"] if event.get("ability_name")] == [
        "Start",
        "End",
    ]
    assert timelines[0]["events"][1]["event_kind"] == "variable"
    assert timelines[0]["events"][1]["ability_names"] == ["Branch", "Middle"]
    assert timelines[0]["events"][2]["ability_name"] == "End"


def test_generated_timelines_merge_same_route_local_permutations():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    long_route = support_events([
        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "A"},
        {"timestamp": "00:04.000", "timestamp_ms": 4000, "ability_name": "B"},
        {"timestamp": "00:07.000", "timestamp_ms": 7000, "ability_name": "C"},
        {"timestamp": "00:10.000", "timestamp_ms": 10000, "ability_name": "D"},
        {"timestamp": "00:13.000", "timestamp_ms": 13000, "ability_name": "E"},
        {"timestamp": "00:16.000", "timestamp_ms": 16000, "ability_name": "F"},
        {"timestamp": "00:19.000", "timestamp_ms": 19000, "ability_name": "G"},
        {"timestamp": "00:22.000", "timestamp_ms": 22000, "ability_name": "H"},
        {"timestamp": "00:25.000", "timestamp_ms": 25000, "ability_name": "I"},
        {"timestamp": "00:28.000", "timestamp_ms": 28000, "ability_name": "J"},
        {"timestamp": "00:31.000", "timestamp_ms": 31000, "ability_name": "K"},
        {"timestamp": "00:34.000", "timestamp_ms": 34000, "ability_name": "L"},
    ])
    permuted_route = support_events([
        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "A"},
        {"timestamp": "00:04.050", "timestamp_ms": 4050, "ability_name": "B"},
        {"timestamp": "00:07.050", "timestamp_ms": 7050, "ability_name": "C"},
        {"timestamp": "00:10.050", "timestamp_ms": 10050, "ability_name": "D"},
        {"timestamp": "00:13.050", "timestamp_ms": 13050, "ability_name": "E"},
        {"timestamp": "00:16.050", "timestamp_ms": 16050, "ability_name": "G"},
        {"timestamp": "00:19.050", "timestamp_ms": 19050, "ability_name": "F"},
        {"timestamp": "00:22.050", "timestamp_ms": 22050, "ability_name": "H"},
        {"timestamp": "00:25.050", "timestamp_ms": 25050, "ability_name": "I"},
        {"timestamp": "00:28.050", "timestamp_ms": 28050, "ability_name": "J"},
        {"timestamp": "00:31.050", "timestamp_ms": 31050, "ability_name": "K"},
        {"timestamp": "00:34.050", "timestamp_ms": 34050, "ability_name": "L"},
    ])

    aligned_reports = [
        {"encounter": {"code": "M11S"}, "report": {"code": "R1"}, "fights": [{"fight_index": 0, "damage_events": long_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "R2"}, "fights": [{"fight_index": 0, "damage_events": permuted_route}]},
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 1


def test_generated_timelines_merge_same_route_alternate_ability_names():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    base_route = support_events([
        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "A"},
        {"timestamp": "00:04.000", "timestamp_ms": 4000, "ability_name": "B"},
        {"timestamp": "00:07.000", "timestamp_ms": 7000, "ability_name": "C"},
        {"timestamp": "00:10.000", "timestamp_ms": 10000, "ability_name": "D"},
        {"timestamp": "00:13.000", "timestamp_ms": 13000, "ability_name": "E"},
        {"timestamp": "00:16.000", "timestamp_ms": 16000, "ability_name": "F"},
        {"timestamp": "00:19.000", "timestamp_ms": 19000, "ability_name": "G"},
        {"timestamp": "00:22.000", "timestamp_ms": 22000, "ability_name": "H"},
        {"timestamp": "00:25.000", "timestamp_ms": 25000, "ability_name": "I"},
        {"timestamp": "00:28.000", "timestamp_ms": 28000, "ability_name": "J"},
        {"timestamp": "00:31.000", "timestamp_ms": 31000, "ability_name": "K"},
        {"timestamp": "00:34.000", "timestamp_ms": 34000, "ability_name": "L"},
    ])
    alternate_route = support_events([
        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "A"},
        {"timestamp": "00:04.050", "timestamp_ms": 4050, "ability_name": "B"},
        {"timestamp": "00:07.050", "timestamp_ms": 7050, "ability_name": "C"},
        {"timestamp": "00:10.050", "timestamp_ms": 10050, "ability_name": "D Prime"},
        {"timestamp": "00:13.050", "timestamp_ms": 13050, "ability_name": "E"},
        {"timestamp": "00:16.050", "timestamp_ms": 16050, "ability_name": "F"},
        {"timestamp": "00:19.050", "timestamp_ms": 19050, "ability_name": "G"},
        {"timestamp": "00:22.050", "timestamp_ms": 22050, "ability_name": "H"},
        {"timestamp": "00:25.050", "timestamp_ms": 25050, "ability_name": "I"},
        {"timestamp": "00:28.050", "timestamp_ms": 28050, "ability_name": "J"},
        {"timestamp": "00:31.050", "timestamp_ms": 31050, "ability_name": "K"},
        {"timestamp": "00:34.050", "timestamp_ms": 34050, "ability_name": "L"},
    ])

    aligned_reports = [
        {"encounter": {"code": "M11S"}, "report": {"code": "R1"}, "fights": [{"fight_index": 0, "damage_events": base_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "R2"}, "fights": [{"fight_index": 0, "damage_events": alternate_route}]},
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 1


def test_generated_timelines_reduce_sample_like_over_split_to_two_branches():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    reference_route = support_events([
        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "A"},
        {"timestamp": "00:04.000", "timestamp_ms": 4000, "ability_name": "Impact"},
        {"timestamp": "00:07.000", "timestamp_ms": 7000, "ability_name": "Sharp Taste"},
        {"timestamp": "00:10.000", "timestamp_ms": 10000, "ability_name": "Heavy Weight"},
        {"timestamp": "00:13.000", "timestamp_ms": 13000, "ability_name": "Sweeping Victory"},
        {"timestamp": "00:16.000", "timestamp_ms": 16000, "ability_name": "Crushing Comet"},
        {"timestamp": "00:19.000", "timestamp_ms": 19000, "ability_name": "Sweeping Victory"},
        {"timestamp": "00:22.000", "timestamp_ms": 22000, "ability_name": "Heavy Weight"},
        {"timestamp": "00:25.000", "timestamp_ms": 25000, "ability_name": "Sharp Taste"},
        {"timestamp": "00:28.000", "timestamp_ms": 28000, "ability_name": "Comet"},
        {"timestamp": "00:31.000", "timestamp_ms": 31000, "ability_name": "Dance of Domination"},
        {"timestamp": "00:34.000", "timestamp_ms": 34000, "ability_name": "Eye of the Hurricane"},
    ])
    same_route_variant = support_events([
        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "A"},
        {"timestamp": "00:04.050", "timestamp_ms": 4050, "ability_name": "Impact"},
        {"timestamp": "00:07.050", "timestamp_ms": 7050, "ability_name": "Sharp Taste"},
        {"timestamp": "00:10.050", "timestamp_ms": 10050, "ability_name": "Heavy Weight"},
        {"timestamp": "00:13.050", "timestamp_ms": 13050, "ability_name": "Sweeping Victory"},
        {"timestamp": "00:16.050", "timestamp_ms": 16050, "ability_name": "Crushing Comet"},
        {"timestamp": "00:19.050", "timestamp_ms": 19050, "ability_name": "Sweeping Victory"},
        {"timestamp": "00:22.050", "timestamp_ms": 22050, "ability_name": "Heavy Weight"},
        {"timestamp": "00:25.050", "timestamp_ms": 25050, "ability_name": "Sharp Taste"},
        {"timestamp": "00:28.050", "timestamp_ms": 28050, "ability_name": "Comet"},
        {"timestamp": "00:31.050", "timestamp_ms": 31050, "ability_name": "Dance of Domination"},
        {"timestamp": "00:34.050", "timestamp_ms": 34050, "ability_name": "Eye of the Hurricane"},
    ])
    divergent_short_route = support_events([
        {"timestamp": "00:01.025", "timestamp_ms": 1025, "ability_name": "A"},
        {"timestamp": "00:06.000", "timestamp_ms": 6000, "ability_name": "Comet"},
        {"timestamp": "00:11.000", "timestamp_ms": 11000, "ability_name": "Explosion"},
        {"timestamp": "00:16.000", "timestamp_ms": 16000, "ability_name": "Shockwave"},
    ])

    aligned_reports = [
        {"encounter": {"code": "M11S"}, "report": {"code": "REF"}, "fights": [{"fight_index": 0, "damage_events": reference_route}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "VAR"}, "fights": [{"fight_index": 0, "damage_events": same_route_variant}]},
        {"encounter": {"code": "M11S"}, "report": {"code": "SHORT"}, "fights": [{"fight_index": 0, "damage_events": divergent_short_route}]},
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 2


def test_generated_timelines_merge_suffix_truncation_into_one_branch():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "LONG1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "Start"},
                        {"timestamp": "00:05.000", "timestamp_ms": 5000, "ability_name": "Middle"},
                        {"timestamp": "00:09.000", "timestamp_ms": 9000, "ability_name": "Enrage 1"},
                        {"timestamp": "00:13.000", "timestamp_ms": 13000, "ability_name": "Enrage 2"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "LONG2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "Start"},
                        {"timestamp": "00:05.050", "timestamp_ms": 5050, "ability_name": "Middle"},
                        {"timestamp": "00:09.050", "timestamp_ms": 9050, "ability_name": "Enrage 1"},
                        {"timestamp": "00:13.050", "timestamp_ms": 13050, "ability_name": "Enrage 2"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "SHORT"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.025", "timestamp_ms": 1025, "ability_name": "Start"},
                        {"timestamp": "00:05.025", "timestamp_ms": 5025, "ability_name": "Middle"},
                    ]),
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 1
    assert [event.get("ability_name") for event in timelines[0]["events"]] == [
        "Start",
        "Middle",
        "Enrage 1",
        "Enrage 2",
    ]


def test_generated_timelines_merge_contained_short_route_with_sparse_interior_gaps():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "LONG"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "Start"},
                        {"timestamp": "00:04.000", "timestamp_ms": 4000, "ability_name": "Shared 1"},
                        {"timestamp": "00:07.000", "timestamp_ms": 7000, "ability_name": "Extra 1"},
                        {"timestamp": "00:10.000", "timestamp_ms": 10000, "ability_name": "Extra 2"},
                        {"timestamp": "00:13.000", "timestamp_ms": 13000, "ability_name": "Shared 2"},
                        {"timestamp": "00:16.000", "timestamp_ms": 16000, "ability_name": "Shared 3"},
                        {"timestamp": "00:19.000", "timestamp_ms": 19000, "ability_name": "Shared 4"},
                        {"timestamp": "00:22.000", "timestamp_ms": 22000, "ability_name": "Shared 5"},
                        {"timestamp": "00:25.000", "timestamp_ms": 25000, "ability_name": "Shared 6"},
                        {"timestamp": "00:28.000", "timestamp_ms": 28000, "ability_name": "Shared 7"},
                        {"timestamp": "00:31.000", "timestamp_ms": 31000, "ability_name": "Tail 1"},
                        {"timestamp": "00:34.000", "timestamp_ms": 34000, "ability_name": "Tail 2"},
                        {"timestamp": "00:37.000", "timestamp_ms": 37000, "ability_name": "Tail 3"},
                        {"timestamp": "00:40.000", "timestamp_ms": 40000, "ability_name": "Tail 4"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "SHORT"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "Start"},
                        {"timestamp": "00:04.050", "timestamp_ms": 4050, "ability_name": "Shared 1"},
                        {"timestamp": "00:13.050", "timestamp_ms": 13050, "ability_name": "Shared 2"},
                        {"timestamp": "00:16.050", "timestamp_ms": 16050, "ability_name": "Shared 3"},
                        {"timestamp": "00:19.050", "timestamp_ms": 19050, "ability_name": "Shared 4"},
                        {"timestamp": "00:22.050", "timestamp_ms": 22050, "ability_name": "Shared 5"},
                        {"timestamp": "00:25.050", "timestamp_ms": 25050, "ability_name": "Shared 6"},
                        {"timestamp": "00:28.050", "timestamp_ms": 28050, "ability_name": "Shared 7"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "DIVERGENT"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.025", "timestamp_ms": 1025, "ability_name": "Start"},
                        {"timestamp": "00:06.000", "timestamp_ms": 6000, "ability_name": "Branch A"},
                        {"timestamp": "00:19.025", "timestamp_ms": 19025, "ability_name": "Shared 4"},
                        {"timestamp": "00:24.000", "timestamp_ms": 24000, "ability_name": "Branch B"},
                        {"timestamp": "00:28.025", "timestamp_ms": 28025, "ability_name": "Shared 7"},
                        {"timestamp": "00:33.000", "timestamp_ms": 33000, "ability_name": "Branch C"},
                    ]),
                }
            ],
        },
    ]

    timelines = sorted(
        build_generated_timelines(aligned_reports),
        key=lambda timeline: (timeline["fight_index"], timeline["branch_index"]),
    )
    assert len(timelines) == 2
    assert [event.get("ability_name") for event in timelines[0]["events"]] == [
        "Start",
        "Shared 1",
        "Shared 2",
        "Shared 3",
        "Shared 4",
        "Shared 5",
        "Shared 6",
        "Shared 7",
        "Tail 1",
        "Tail 2",
        "Tail 3",
        "Tail 4",
    ]


def test_generated_timelines_keep_tail_but_drop_interior_noise():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "LONG"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "Start"},
                        {"timestamp": "00:03.000", "timestamp_ms": 3000, "ability_name": "Noise"},
                        {"timestamp": "00:05.000", "timestamp_ms": 5000, "ability_name": "Middle"},
                        {"timestamp": "00:09.000", "timestamp_ms": 9000, "ability_name": "Enrage 1"},
                        {"timestamp": "00:13.000", "timestamp_ms": 13000, "ability_name": "Enrage 2"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "SHORT1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "Start"},
                        {"timestamp": "00:05.050", "timestamp_ms": 5050, "ability_name": "Middle"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "SHORT2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.025", "timestamp_ms": 1025, "ability_name": "Start"},
                        {"timestamp": "00:05.025", "timestamp_ms": 5025, "ability_name": "Middle"},
                    ]),
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 1
    assert [event.get("ability_name") for event in timelines[0]["events"]] == [
        "Start",
        "Middle",
        "Enrage 1",
        "Enrage 2",
    ]


def test_generated_timelines_reject_rare_noise_events_below_threshold():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "Stable"},
                        {"timestamp": "00:07.000", "timestamp_ms": 7000, "ability_name": "Noise"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.100", "timestamp_ms": 1100, "ability_name": "Stable"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R3"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:00.950", "timestamp_ms": 950, "ability_name": "Stable"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R4"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 4,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.050", "timestamp_ms": 1050, "ability_name": "Stable"},
                    ]),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R5"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 5,
                    "fight_name": "The Tyrant",
                    "damage_events": support_events([
                        {"timestamp": "00:01.025", "timestamp_ms": 1025, "ability_name": "Stable"},
                    ]),
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines) == 1
    assert [event.get("ability_name") for event in timelines[0]["events"]] == ["Stable"]


def test_generated_timelines_use_median_damage_over_vulnerability_outliers():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.000",
                            "timestamp_ms": 1000,
                            "ability_name": "Buster",
                            "unmitigated_damage": 100000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                            "multiplier": 1.0,
                        }
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.050",
                            "timestamp_ms": 1050,
                            "ability_name": "Buster",
                            "unmitigated_damage": 110000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                            "multiplier": 1.0,
                        }
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R3"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.025",
                            "timestamp_ms": 1025,
                            "ability_name": "Buster",
                            "unmitigated_damage": 120000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                            "multiplier": 1.0,
                        }
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R4"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 4,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.010",
                            "timestamp_ms": 1010,
                            "ability_name": "Buster",
                            "unmitigated_damage": 240000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                            "multiplier": 2.0,
                        }
                    ],
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert timelines[0]["events"][0]["unmitigated_damage"] == 115000


def test_generated_timelines_use_direct_median_damage_sample_for_raidwides():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "party_size": 8,
                    "damage_events": make_party_events(
                        timestamp_ms=1000,
                        ability_name="Heavy Hitter",
                        target_count=6,
                        damage=100000,
                    ),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "party_size": 8,
                    "damage_events": make_party_events(
                        timestamp_ms=1050,
                        ability_name="Heavy Hitter",
                        target_count=5,
                        damage=200000,
                    ),
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert timelines[0]["events"][0]["classification"] == "raidwide"
    assert timelines[0]["events"][0]["unmitigated_damage"] == 100000


def test_generated_timelines_normalize_damage_when_no_base_hits_exist():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.000",
                            "timestamp_ms": 1000,
                            "ability_name": "Magic Hit",
                            "unmitigated_damage": 150000,
                            "ability_type": "magical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                            "multiplier": 1.5,
                        }
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.040",
                            "timestamp_ms": 1040,
                            "ability_name": "Magic Hit",
                            "unmitigated_damage": 200000,
                            "ability_type": "magical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                            "multiplier": 2.0,
                        }
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R3"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:00.980",
                            "timestamp_ms": 980,
                            "ability_name": "Magic Hit",
                            "unmitigated_damage": 300000,
                            "ability_type": "magical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                            "multiplier": 3.0,
                        }
                    ],
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert timelines[0]["events"][0]["unmitigated_damage"] == 100000


def test_generated_timelines_classify_shared_busters_and_pairs():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.000",
                            "timestamp_ms": 1000,
                            "ability_name": "Shared Buster",
                            "unmitigated_damage": 180000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.200",
                            "timestamp_ms": 1200,
                            "ability_name": "Shared Buster",
                            "unmitigated_damage": 181000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Paladin",
                            "target_name": "Tank Two",
                            "is_dot": False,
                        },
                    ] + make_party_events(
                        timestamp_ms=6000,
                        ability_name="Small Party Hit",
                        target_count=4,
                        damage=90000,
                        ability_type="magical",
                    ),
                }
            ],
        }
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert timelines[0]["events"][0]["event_kind"] == "stable"
    assert timelines[0]["events"][0]["classification"] == "dual_tankbuster"
    assert timelines[0]["events"][0]["is_multi_hit"] is False
    assert timelines[0]["events"][1]["event_kind"] == "stable"
    assert timelines[0]["events"][1]["classification"] == "small_party"
    assert timelines[0]["events"][1]["is_multi_hit"] is False


def test_generated_timelines_classify_staggered_two_tank_hits_by_report_local_window():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.000",
                            "timestamp_ms": 1000,
                            "ability_name": "Raw Steel",
                            "unmitigated_damage": 400000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.250",
                            "timestamp_ms": 1250,
                            "ability_name": "Raw Steel",
                            "unmitigated_damage": 410000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Paladin",
                            "target_name": "Tank Two",
                            "is_dot": False,
                        },
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.050",
                            "timestamp_ms": 1050,
                            "ability_name": "Raw Steel",
                            "unmitigated_damage": 405000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "DarkKnight",
                            "target_name": "Tank Alpha",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.300",
                            "timestamp_ms": 1300,
                            "ability_name": "Raw Steel",
                            "unmitigated_damage": 415000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Gunbreaker",
                            "target_name": "Tank Beta",
                            "is_dot": False,
                        },
                    ],
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert timelines[0]["events"][0]["classification"] == "dual_tankbuster"


def test_generated_timelines_classify_combined_tank_buster_and_multi_target_per_ability():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.000",
                            "timestamp_ms": 1000,
                            "ability_name": "Impact",
                            "unmitigated_damage": 140000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Dancer",
                            "target_name": "DPS One",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.020",
                            "timestamp_ms": 1020,
                            "ability_name": "Impact",
                            "unmitigated_damage": 140000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Monk",
                            "target_name": "DPS Two",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.040",
                            "timestamp_ms": 1040,
                            "ability_name": "Impact",
                            "unmitigated_damage": 140000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Pictomancer",
                            "target_name": "DPS Three",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.060",
                            "timestamp_ms": 1060,
                            "ability_name": "Impact",
                            "unmitigated_damage": 140000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Reaper",
                            "target_name": "DPS Four",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.080",
                            "timestamp_ms": 1080,
                            "ability_name": "Impact",
                            "unmitigated_damage": 140000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Scholar",
                            "target_name": "Healer One",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.100",
                            "timestamp_ms": 1100,
                            "ability_name": "Impact",
                            "unmitigated_damage": 140000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "WhiteMage",
                            "target_name": "Healer Two",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.150",
                            "timestamp_ms": 1150,
                            "ability_name": "Raw Steel",
                            "unmitigated_damage": 400000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.300",
                            "timestamp_ms": 1300,
                            "ability_name": "Raw Steel",
                            "unmitigated_damage": 410000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Paladin",
                            "target_name": "Tank Two",
                            "is_dot": False,
                        },
                    ],
                }
            ],
        }
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert timelines[0]["events"][0]["event_kind"] == "combined"
    assert timelines[0]["events"][0]["classification"] == [
        "raidwide",
        "dual_tankbuster",
    ]
    assert timelines[0]["events"][0]["is_multi_hit"] == [False, False]


def test_generated_timelines_use_dominant_mechanic_profile_for_mixed_samples():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.000",
                            "timestamp_ms": 1000,
                            "ability_name": "Foregone Fatality",
                            "unmitigated_damage": 200000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Warrior",
                            "target_name": "Tank One",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.200",
                            "timestamp_ms": 1200,
                            "ability_name": "Foregone Fatality",
                            "unmitigated_damage": 205000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Paladin",
                            "target_name": "Tank Two",
                            "is_dot": False,
                        },
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.050",
                            "timestamp_ms": 1050,
                            "ability_name": "Foregone Fatality",
                            "unmitigated_damage": 207000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "DarkKnight",
                            "target_name": "Tank Alpha",
                            "is_dot": False,
                        },
                        {
                            "timestamp": "00:01.250",
                            "timestamp_ms": 1250,
                            "ability_name": "Foregone Fatality",
                            "unmitigated_damage": 202000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Gunbreaker",
                            "target_name": "Tank Beta",
                            "is_dot": False,
                        },
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R3"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.100",
                            "timestamp_ms": 1100,
                            "ability_name": "Foregone Fatality",
                            "unmitigated_damage": 90000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Pictomancer",
                            "target_name": "Caster",
                            "is_dot": False,
                        }
                    ],
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert timelines[0]["events"][0]["classification"] == "dual_tankbuster"

def test_generated_timelines_drop_ambiguous_mixed_classifications():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": make_party_events(
                        timestamp_ms=1000,
                        ability_name="Mixed Profile",
                        target_count=6,
                        damage=180000,
                    ),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": make_party_events(
                        timestamp_ms=1050,
                        ability_name="Mixed Profile",
                        target_count=4,
                        damage=90000,
                    ),
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert timelines[0]["events"] == []


def test_generated_timelines_keep_single_target_actions_as_stable():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.000",
                            "timestamp_ms": 1000,
                            "ability_name": "Single Hit",
                            "unmitigated_damage": 120000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Pictomancer",
                            "target_name": "Winny Leika",
                            "is_dot": False,
                        }
                    ],
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": [
                        {
                            "timestamp": "00:01.050",
                            "timestamp_ms": 1050,
                            "ability_name": "Single Hit",
                            "unmitigated_damage": 121000,
                            "ability_type": "physical",
                            "hit_type": "landed",
                            "target_subtype": "Pictomancer",
                            "target_name": "Winny Leika",
                            "is_dot": False,
                        }
                    ],
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert timelines[0]["events"] == []


def test_generated_timelines_collapse_dot_ticks_into_single_event_with_duration():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": make_party_dot_run(
                        start_timestamps_ms=[1000, 4000, 7000],
                        ability_name="Burn",
                        target_count=6,
                        damage=10000,
                    ),
                }
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 2,
                    "fight_name": "The Tyrant",
                    "damage_events": make_party_dot_run(
                        start_timestamps_ms=[1100, 4100, 7100],
                        ability_name="Burn",
                        target_count=6,
                        damage=11000,
                    ),
                }
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert len(timelines[0]["events"]) == 1
    assert timelines[0]["events"][0]["ability_name"] == "Burn"
    assert timelines[0]["events"][0]["is_dot"] is True
    assert timelines[0]["events"][0]["is_multi_hit"] is False
    assert timelines[0]["events"][0]["classification"] == "raidwide"
    assert timelines[0]["events"][0]["duration_ms"] == 6000
    assert timelines[0]["events"][0]["unmitigated_damage"] == 10500


def test_generated_timelines_split_separated_dot_runs():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "The Tyrant",
                    "damage_events": (
                        make_party_dot_run(
                            start_timestamps_ms=[1000, 4000],
                            ability_name="Burn",
                            target_count=6,
                            damage=10000,
                        )
                        + make_party_dot_run(
                            start_timestamps_ms=[12000, 15000],
                            ability_name="Burn",
                            target_count=6,
                            damage=10000,
                        )
                    ),
                }
            ],
        }
    ]

    timelines = build_generated_timelines(aligned_reports)
    assert [event["ability_name"] for event in timelines[0]["events"]] == ["Burn", "Burn"]
    assert [event["duration_ms"] for event in timelines[0]["events"]] == [3000, 3000]
    assert [event["classification"] for event in timelines[0]["events"]] == ["raidwide", "raidwide"]


def test_generated_timelines_keep_multiple_fight_indexes_separate():
    from fflogs_damage_timeline.postprocess import build_generated_timelines

    aligned_reports = [
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R1"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 1,
                    "fight_name": "Fight 0",
                    "damage_events": [{"timestamp": "00:01.000", "timestamp_ms": 1000, "ability_name": "A"}],
                },
                {
                    "fight_index": 1,
                    "fight_id": 2,
                    "fight_name": "Fight 1",
                    "damage_events": [{"timestamp": "00:02.000", "timestamp_ms": 2000, "ability_name": "B"}],
                },
            ],
        },
        {
            "encounter": {"code": "M11S"},
            "report": {"code": "R2"},
            "fights": [
                {
                    "fight_index": 0,
                    "fight_id": 3,
                    "fight_name": "Fight 0",
                    "damage_events": [{"timestamp": "00:01.100", "timestamp_ms": 1100, "ability_name": "A"}],
                },
                {
                    "fight_index": 1,
                    "fight_id": 4,
                    "fight_name": "Fight 1",
                    "damage_events": [{"timestamp": "00:02.100", "timestamp_ms": 2100, "ability_name": "B"}],
                },
            ],
        },
    ]

    timelines = build_generated_timelines(aligned_reports)
    fight_indexes = sorted(timeline["fight_index"] for timeline in timelines)
    assert fight_indexes == [0, 1]
