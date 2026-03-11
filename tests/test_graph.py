"""Tests for the LangGraph timeline generation pipeline."""

import pytest
from unittest.mock import AsyncMock, patch

from xiv_timeline.graph import (
    TimelineState,
    build_graph,
    fetch_cactbot_node,
    fetch_guides_node,
    export_node,
    append_damage_node,
    _summarize_entries,
    _summarize_guides,
    _summarize_damage,
    SynthesizedTimeline,
)


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------


def test_state_schema_accepts_required_fields():
    state: TimelineState = {
        "boss_name": "p12s",
        "expansion": "06-ew",
        "encounter_type": "raid",
        "difficulty": "s",
    }
    assert state["boss_name"] == "p12s"


def test_state_schema_accepts_all_fields():
    state: TimelineState = {
        "boss_name": "p12s",
        "expansion": "06-ew",
        "encounter_type": "raid",
        "difficulty": "s",
        "cactbot_data": {"entries": []},
        "guide_data": {"guides": {}},
        "damage_data": {},
        "synthesized": {"boss_name": "test"},
        "cactbot_export": "export text",
        "cactbot_raw": "raw text",
    }
    assert state["cactbot_export"] == "export text"


# ---------------------------------------------------------------------------
# Graph compilation
# ---------------------------------------------------------------------------


def test_graph_compiles():
    graph = build_graph()
    assert graph is not None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def test_summarize_entries_empty():
    assert _summarize_entries([]) == "(no timeline entries found)"


def test_summarize_entries_basic():
    entries = [
        {"timestamp": 10.5, "ability_name": "Megaflare"},
        {"timestamp": 20.0, "ability_name": "Tank Buster"},
    ]
    result = _summarize_entries(entries)
    assert "Megaflare" in result
    assert "Tank Buster" in result
    assert "10.5" in result


def test_summarize_entries_multi_hit():
    entries = [
        {
            "timestamp": 5.0,
            "ability_name": "Triple Attack",
            "is_multi_hit": True,
            "hit_count": 3,
        },
    ]
    result = _summarize_entries(entries)
    assert "x3 hits" in result


def test_summarize_entries_truncation():
    entries = [{"timestamp": float(i), "ability_name": f"Ability {i}"} for i in range(100)]
    result = _summarize_entries(entries, max_entries=10)
    assert "... and 90 more entries" in result


def test_summarize_guides_empty():
    assert _summarize_guides({"guides": {}}) == "(no guide content)"


def test_summarize_guides_with_content():
    guide_data = {
        "guides": {
            "icy-veins": {
                "success": True,
                "content": {
                    "overview": "This is a test boss guide overview.",
                    "phases": [{"title": "Phase 1", "content": "Do thing A."}],
                },
            }
        }
    }
    result = _summarize_guides(guide_data)
    assert "icy-veins" in result
    assert "test boss guide" in result
    assert "Phase 1" in result


# ---------------------------------------------------------------------------
# Node tests (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_cactbot_node():
    mock_data = {
        "boss_name": "p12s",
        "entries": [{"timestamp": 0, "ability_name": "Test"}],
        "raw_content": "raw timeline text",
    }

    with patch("xiv_timeline.graph.CactbotClient") as MockClient:
        instance = MockClient.return_value
        instance.fetch_timeline = AsyncMock(return_value=mock_data)
        instance.close = AsyncMock()

        state: TimelineState = {"boss_name": "p12s", "expansion": "06-ew"}
        result = await fetch_cactbot_node(state)

        assert "cactbot_data" in result
        assert result["cactbot_data"]["boss_name"] == "p12s"
        assert result["cactbot_raw"] == "raw timeline text"
        instance.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_guides_node():
    mock_data = {"boss_name": "p12s", "guides": {"icy-veins": {"success": True}}}

    with patch("xiv_timeline.graph.GuideAgent") as MockAgent:
        instance = MockAgent.return_value
        instance.fetch_all_guides = AsyncMock(return_value=mock_data)
        instance.close = AsyncMock()

        state: TimelineState = {"boss_name": "p12s"}
        result = await fetch_guides_node(state)

        assert "guide_data" in result
        assert result["guide_data"]["boss_name"] == "p12s"
        instance.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_export_node():
    state: TimelineState = {
        "boss_name": "test",
        "synthesized": {
            "boss_name": "Test Boss",
            "expansion": "06-ew",
            "encounter_type": "raid",
            "phases": [
                {
                    "name": "Phase 1",
                    "entries": [
                        {
                            "timestamp": 5.0,
                            "ability_name": "Megaflare",
                            "ability_id": "999",
                            "source": "Boss",
                        },
                    ],
                }
            ],
            "notes": ["Watch out!"],
        },
    }
    result = await export_node(state)
    assert "cactbot_export" in result
    assert "Megaflare" in result["cactbot_export"]


# ---------------------------------------------------------------------------
# New tests for damage summarization and enriched fields
# ---------------------------------------------------------------------------


def test_summarize_damage_empty():
    assert _summarize_damage({}) == "(no damage data available)"


def test_summarize_damage_with_data():
    data = {
        "Honey B. Finale": {
            "unmitigated_damage_70th": 71519,
            "damage_min": 55000,
            "damage_max": 85000,
            "ability_type": "Raidwide",
            "is_dot": False,
            "target_count_avg": 8.0,
            "damage_samples": 10,
        }
    }
    result = _summarize_damage(data)
    assert "Honey B. Finale" in result
    assert "Raidwide" in result
    assert "71,519" in result


def test_summarize_damage_dot():
    data = {
        "Poison Sting": {
            "unmitigated_damage_70th": 5000,
            "damage_min": 3000,
            "damage_max": 7000,
            "ability_type": None,
            "is_dot": True,
            "target_count_avg": 1.0,
            "damage_samples": 5,
        }
    }
    result = _summarize_damage(data)
    assert "DOT" in result


@pytest.mark.asyncio
async def test_append_damage_node_enriched_fields():
    state: TimelineState = {
        "boss_name": "test",
        "synthesized": {
            "phases": [
                {
                    "name": "Phase 1",
                    "entries": [
                        {"timestamp": 5.0, "ability_name": "Honey B. Finale"},
                        {"timestamp": 10.0, "ability_name": "Unknown Ability"},
                    ],
                }
            ],
        },
        "damage_data": {
            "Honey B. Finale": {
                "unmitigated_damage_70th": 71519,
                "ability_type": "Raidwide",
                "is_dot": False,
                "damage_min": 55000,
                "damage_max": 85000,
                "damage_median": 70000,
                "target_count_avg": 8.0,
                "ability_game_id": "9B86",
            }
        },
    }
    result = await append_damage_node(state)
    entries = result["synthesized"]["phases"][0]["entries"]

    # Only the matched entry should remain (Unknown Ability filtered out)
    assert len(entries) == 1
    matched = entries[0]
    assert matched["unmitigated_damage"] == 71519
    assert matched["ability_type"] == "Raidwide"
    assert matched["damage_min"] == 55000
    assert matched["damage_max"] == 85000
    assert matched["damage_median"] == 70000
    assert matched["target_count"] == 8.0

    # fflogs_reference should contain ALL entries (pre-filter) in timeline order
    ref = result.get("fflogs_reference", [])
    assert len(ref) == 2
    assert ref[0]["ability_name"] == "Honey B. Finale"
    assert ref[1]["ability_name"] == "Unknown Ability"
    assert ref[0].get("phase") == "Phase 1"


@pytest.mark.asyncio
async def test_export_node_with_damage_ranges():
    state: TimelineState = {
        "boss_name": "test",
        "synthesized": {
            "boss_name": "Test Boss",
            "expansion": "06-ew",
            "encounter_type": "raid",
            "phases": [
                {
                    "name": "Phase 1",
                    "entries": [
                        {
                            "timestamp": 5.0,
                            "ability_name": "Big Hit",
                            "ability_id": "ABC1",
                            "unmitigated_damage": 70000,
                            "damage_min": 55000,
                            "damage_max": 85000,
                            "ability_type": "Raidwide",
                            "mitigation_note": "Reprisal+Samba",
                        },
                    ],
                }
            ],
            "notes": [],
        },
    }
    result = await export_node(state)
    export_text = result["cactbot_export"]
    assert "70,000" in export_text
    assert "55,000" in export_text
    assert "85,000" in export_text
    assert "Raidwide" in export_text


@pytest.mark.asyncio
async def test_append_damage_filters_no_damage_entries():
    """Entries without damage data are removed; empty phases are pruned."""
    state: TimelineState = {
        "boss_name": "test",
        "synthesized": {
            "phases": [
                {
                    "name": "Phase 1",
                    "entries": [
                        {"timestamp": 5.0, "ability_name": "Big Hit"},
                        {"timestamp": 10.0, "ability_name": "No Damage Move"},
                    ],
                },
                {
                    "name": "Phase 2",
                    "entries": [
                        {"timestamp": 20.0, "ability_name": "Also No Damage"},
                    ],
                },
            ],
        },
        "damage_data": {
            "Big Hit": {
                "unmitigated_damage_70th": 50000,
                "ability_type": "Raidwide",
                "is_dot": False,
                "damage_min": 40000,
                "damage_max": 60000,
                "damage_median": 50000,
                "target_count_avg": 8.0,
            }
        },
    }
    result = await append_damage_node(state)
    phases = result["synthesized"]["phases"]

    # Phase 2 should be pruned (all entries had no damage)
    assert len(phases) == 1
    assert phases[0]["name"] == "Phase 1"

    # Only "Big Hit" should remain in Phase 1
    entries = phases[0]["entries"]
    assert len(entries) == 1
    assert entries[0]["ability_name"] == "Big Hit"
    assert entries[0]["unmitigated_damage"] == 50000
