import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

def test_encounter_loader_finds_m11s():
    """Integration: EncounterLoader can find M11S with correct data."""
    os.environ["FFLOGS_CLIENT_ID"] = "test"
    os.environ["FFLOGS_CLIENT_SECRET"] = "test"
    from fflogs.encounters import EncounterLoader
    loader = EncounterLoader(Path("/Users/eugene/Documents/Github/XIVTimelineGenerator/data/encounters"))
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
    loader = EncounterLoader(Path("/Users/eugene/Documents/Github/XIVTimelineGenerator/data/encounters"))
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
    loader = EncounterLoader(Path("/Users/eugene/Documents/Github/XIVTimelineGenerator/data/encounters"))
    encounters = loader.load_expansion("dawntrail")
    codes = [e.code for e in encounters]
    expected = ["M1S", "M2S", "M3S", "M4S", "M5S", "M6S", "M7S", "M8S",
                "M9S", "M10S", "M11S", "M12S", "FRU"]
    for code in expected:
        assert code in codes, f"{code} not found in encounters"

def test_all_endwalker_encounters_load():
    """Integration: All Endwalker encounters load without error."""
    from fflogs.encounters import EncounterLoader
    loader = EncounterLoader(Path("/Users/eugene/Documents/Github/XIVTimelineGenerator/data/encounters"))
    encounters = loader.load_expansion("endwalker")
    codes = [e.code for e in encounters]
    expected = ["P1S", "P2S", "P3S", "P4S", "P5S", "P6S", "P7S", "P8S",
                "P9S", "P10S", "P11S", "P12S", "TOP", "DSR"]
    for code in expected:
        assert code in codes, f"{code} not found in encounters"


# ----------------------------------------------------------------------
# fflogs_damage_timeline integration tests
# ----------------------------------------------------------------------

class TestFilters:
    """Tests for filter functions."""

    @pytest.fixture
    def mock_events(self):
        return [
            {"timestamp": 1000, "targetID": 1, "sourceID": 100, "abilityGameID": 2000, "hitType": 2, "amount": 5000},
            {"timestamp": 1000, "targetID": 1, "sourceID": 100, "abilityGameID": 50, "hitType": 2, "amount": 1000},  # auto-attack
            {"timestamp": 1500, "targetID": 1, "sourceID": 100, "abilityGameID": 2000, "hitType": 1, "amount": 0},  # miss
            {"timestamp": 2000, "targetID": 2, "sourceID": 100, "abilityGameID": 2000, "hitType": 2, "amount": 3000},  # non-player target
        ]

    @pytest.fixture
    def mock_actors(self):
        return {
            1: {"id": 1, "name": "Player1", "subType": "Player", "type": "Actor"},
            2: {"id": 2, "name": "OtherNPC", "subType": "NPC", "type": "Actor"},
            100: {"id": 100, "name": "Boss", "subType": "Boss", "type": "Actor"},
        }

    def test_filter_removes_auto_attacks(self, mock_events, mock_actors):
        """Filter removes auto-attacks (abilityGameID < 100)."""
        from fflogs_damage_timeline.filters import filter_damage_events
        result = filter_damage_events(mock_events, mock_actors)
        ability_ids = [e["abilityGameID"] for e in result]
        for aid in ability_ids:
            assert aid >= 100, f"abilityGameID {aid} should not be in result"

    def test_filter_removes_misses(self, mock_events, mock_actors):
        """Filter removes misses (hitType == 1)."""
        from fflogs_damage_timeline.filters import filter_damage_events
        result = filter_damage_events(mock_events, mock_actors)
        for e in result:
            assert e["hitType"] != 1, "miss events should not be in result"

    def test_filter_removes_non_player_targets(self, mock_events, mock_actors):
        """Filter removes non-player targets."""
        from fflogs_damage_timeline.filters import filter_damage_events
        result = filter_damage_events(mock_events, mock_actors)
        for e in result:
            target = mock_actors.get(e["targetID"])
            assert target is not None and target["subType"] == "Player"

    def test_filter_only_keeps_valid_events(self, mock_events, mock_actors):
        """Filter only keeps events that pass all filters."""
        from fflogs_damage_timeline.filters import filter_damage_events
        result = filter_damage_events(mock_events, mock_actors)
        # Only event 0 (timestamp 1000, ability 2000, hitType 2, target Player) should pass
        assert len(result) == 1
        assert result[0]["timestamp"] == 1000
        assert result[0]["abilityGameID"] == 2000


class TestNormalizer:
    """Tests for timestamp normalizer."""

    def test_normalizer_subtracts_fight_start_time(self):
        """Normalizer subtracts fight_start_time correctly."""
        from fflogs_damage_timeline.normalizer import normalize_timestamps
        events = [
            {"timestamp": 5000, "data": "a"},
            {"timestamp": 5500, "data": "b"},
            {"timestamp": 6000, "data": "c"},
        ]
        result = normalize_timestamps(events, fight_start_time=5000)
        assert result[0]["timestamp"] == 0
        assert result[1]["timestamp"] == 500
        assert result[2]["timestamp"] == 1000

    def test_normalizer_does_not_mutate_original_events(self):
        """Normalizer does not mutate original events."""
        from fflogs_damage_timeline.normalizer import normalize_timestamps
        original = [{"timestamp": 5000, "data": "a"}]
        original_copy = [{"timestamp": 5000, "data": "a"}]
        normalize_timestamps(original, fight_start_time=1000)
        assert original == original_copy

    def test_normalizer_handles_empty_list(self):
        """Normalizer handles empty event list."""
        from fflogs_damage_timeline.normalizer import normalize_timestamps
        result = normalize_timestamps([], fight_start_time=5000)
        assert result == []


class TestOutput:
    """Tests for timeline output."""

    @pytest.fixture
    def mock_fight_data(self):
        return {
            "encounter": {"id": 73, "name": "The Tyrant"},
            "fight": {"fight_id": 5, "startTime": 5000, "endTime": 60000},
            "report": {"code": "ABC123", "title": "Test Report"},
        }

    @pytest.fixture
    def mock_events(self):
        return [
            {"timestamp": 0, "targetID": 1, "sourceID": 100, "abilityGameID": 2000, "hitType": 2, "amount": 5000},
            {"timestamp": 500, "targetID": 1, "sourceID": 100, "abilityGameID": 2001, "hitType": 2, "amount": 3000},
        ]

    def test_output_creates_correct_json_structure(self, tmp_path, mock_fight_data, mock_events):
        """Output creates correct JSON structure."""
        from fflogs_damage_timeline.output import write_timeline
        result = write_timeline(tmp_path, "M11S", mock_fight_data, mock_events)
        assert result.exists()
        with result.open() as f:
            data = json.load(f)
        assert "encounter" in data
        assert "fight" in data
        assert "report" in data
        assert "damage_events" in data
        assert data["encounter"]["id"] == 73
        assert data["fight"]["fight_id"] == 5
        assert len(data["damage_events"]) == 2

    def test_output_creates_directory_if_not_exists(self, tmp_path, mock_fight_data, mock_events):
        """Output creates directory if not exists."""
        from fflogs_damage_timeline.output import write_timeline
        output_dir = tmp_path / "nested" / "path"
        result = write_timeline(output_dir, "M11S", mock_fight_data, mock_events)
        assert result.parent.parent.exists()

    def test_output_skips_existing_files(self, tmp_path, mock_fight_data, mock_events):
        """Output skips existing files."""
        from fflogs_damage_timeline.output import write_timeline
        # Write first time
        result1 = write_timeline(tmp_path, "M11S", mock_fight_data, mock_events)
        # Modify file
        result1.write_text("modified")
        # Write second time - should skip
        result2 = write_timeline(tmp_path, "M11S", mock_fight_data, mock_events)
        assert result1 == result2
        assert result1.read_text() == "modified"


class TestFullPipeline:
    """End-to-end tests with mocked GraphQL client."""

    @pytest.fixture
    def mock_graphql_client(self):
        """Create a mock GraphQL client with test data."""
        mock_client = MagicMock()
        # Mock reports response
        mock_client.fetch_reports.return_value = [
            {"code": "ABC123", "title": "Test Fight", "startTime": 1000, "endTime": 60000}
        ]
        # Mock fights response
        mock_client.fetch_fights.return_value = [
            {"id": 5, "startTime": 5000, "endTime": 60000, "encounterID": 73, "difficulty": 101}
        ]
        # Mock events response
        mock_client.fetch_events.return_value = [
            {"timestamp": 5000, "targetID": 1, "sourceID": 100, "abilityGameID": 2000, "hitType": 2, "amount": 5000},
            {"timestamp": 5500, "targetID": 1, "sourceID": 100, "abilityGameID": 50, "hitType": 2, "amount": 1000},  # auto-attack
            {"timestamp": 6000, "targetID": 1, "sourceID": 100, "abilityGameID": 2000, "hitType": 1, "amount": 0},  # miss
            {"timestamp": 6500, "targetID": 2, "sourceID": 100, "abilityGameID": 2001, "hitType": 2, "amount": 3000},  # non-player target
            {"timestamp": 7000, "targetID": 1, "sourceID": 100, "abilityGameID": 2002, "hitType": 2, "amount": 4000},
        ]
        return mock_client

    @pytest.fixture
    def mock_actors(self):
        return {
            1: {"id": 1, "name": "Tank", "subType": "Player", "type": "Actor"},
            2: {"id": 2, "name": "NPC", "subType": "NPC", "type": "Actor"},
            100: {"id": 100, "name": "Boss", "subType": "Boss", "type": "Actor"},
        }

    def test_full_pipeline_with_mocked_client(self, mock_graphql_client, mock_actors, tmp_path):
        """Full pipeline: fetch -> filter -> normalize -> output with mocked client."""
        from fflogs_damage_timeline.filters import filter_damage_events
        from fflogs_damage_timeline.normalizer import normalize_timestamps
        from fflogs_damage_timeline.output import write_timeline

        # Fetch (mocked)
        reports = mock_graphql_client.fetch_reports(zone_id=73, encounter_id=999)
        fights = mock_graphql_client.fetch_fights(report_code="ABC123", encounter_id=999)
        events = mock_graphql_client.fetch_events(report_code="ABC123", fight_id=5, start_time=5000, end_time=60000)

        # Filter
        filtered = filter_damage_events(events, mock_actors)
        # Should only have events with:
        # - abilityGameID >= 100 (no auto-attacks)
        # - hitType != 1 (no misses)
        # - target is Player (targetID 1)
        assert len(filtered) == 2
        assert all(e["abilityGameID"] >= 100 for e in filtered)
        assert all(e["hitType"] != 1 for e in filtered)
        assert all(mock_actors.get(e["targetID"], {}).get("subType") == "Player" for e in filtered)

        # Normalize
        fight_start_time = 5000
        normalized = normalize_timestamps(filtered, fight_start_time)
        assert normalized[0]["timestamp"] == 0
        assert normalized[1]["timestamp"] == 2000

        # Output
        fight_data = {
            "encounter": {"id": 73, "name": "The Tyrant"},
            "fight": {"fight_id": 5, "startTime": 5000, "endTime": 60000},
            "report": {"code": "ABC123", "title": "Test Fight"},
        }
        result = write_timeline(tmp_path, "M11S", fight_data, normalized)
        assert result.exists()
        with result.open() as f:
            data = json.load(f)
        assert len(data["damage_events"]) == 2
        assert data["damage_events"][0]["timestamp"] == 0
