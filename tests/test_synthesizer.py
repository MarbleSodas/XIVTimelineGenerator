"""Tests for the timeline synthesizer."""

import pytest
from xiv_timeline.synthesizer import TimelineSynthesizer


def test_synthesizer_basic():
    cactbot_data = {
        "boss_name": "Test Boss",
        "expansion": "06-ew",
        "encounter_type": "raid",
        "difficulty": "s",
        "source_url": "http://example.com/cactbot",
        "entries": [
            {
                "timestamp": 0.0,
                "ability_name": "Test Attack",
                "ability_id": "123",
                "source": "Boss",
            }
        ],
        "phases": [
            {
                "name": "Phase 1",
                "start_time": 0.0,
                "entries": [
                    {"timestamp": 0.0, "ability_name": "Test Attack"},
                ],
            }
        ],
    }
    guide_data = {"guides": {}}

    synthesizer = TimelineSynthesizer()
    result = synthesizer.synthesize(cactbot_data, guide_data)

    assert result["boss_name"] == "Test Boss"
    assert len(result["phases"]) == 1
    assert result["phases"][0]["name"] == "Phase 1"
    assert result["confidence"] > 0.0


def test_generate_cactbot_export():
    synthesizer = TimelineSynthesizer()
    data = {
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
                    }
                ],
            }
        ],
        "notes": ["Watch out!"],
    }

    export = synthesizer.generate_cactbot_export(data)
    assert "### Test Boss" in export
    assert '5.0 "Megaflare"' in export
    assert "# Watch out!" in export
