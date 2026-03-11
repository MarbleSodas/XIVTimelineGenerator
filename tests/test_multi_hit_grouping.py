"""Tests for multi-hit ability grouping logic."""

import pytest
from xiv_timeline.graph import (
    _extract_xn_multiplier,
    _get_base_ability_name,
    _group_multi_hit_entries,
    _finalize_hit_group,
)


# ---------------------------------------------------------------------------
# _get_base_ability_name tests
# ---------------------------------------------------------------------------


class TestGetBaseAbilityName:
    def test_strips_trailing_number(self):
        assert _get_base_ability_name("Flame Floater 1") == "Flame Floater"
        assert _get_base_ability_name("Hot Aerial 3") == "Hot Aerial"
        assert _get_base_ability_name("Cutback Blaze 2") == "Cutback Blaze"

    def test_strips_trailing_parenthetical(self):
        assert _get_base_ability_name("Xtreme Spectacular (line)") == "Xtreme Spectacular"
        assert _get_base_ability_name("Xtreme Spectacular (big)") == "Xtreme Spectacular"
        assert _get_base_ability_name("Ability (cast)") == "Ability"

    def test_strips_both(self):
        # parenthetical stripped first, then number — so "Ability 1 (line)" → "Ability"
        assert _get_base_ability_name("Ability 1 (line)") == "Ability"

    def test_no_suffix(self):
        assert _get_base_ability_name("Re-entry Blast") == "Re-entry Blast"
        assert _get_base_ability_name("Hot Impact") == "Hot Impact"
        assert _get_base_ability_name("Deep Impact") == "Deep Impact"

    def test_strips_x_multiplier(self):
        assert _get_base_ability_name("Xtreme Spectacular x6") == "Xtreme Spectacular"
        assert _get_base_ability_name("Ability x12") == "Ability"

    def test_empty_string(self):
        assert _get_base_ability_name("") == ""


# ---------------------------------------------------------------------------
# _extract_xn_multiplier tests
# ---------------------------------------------------------------------------


class TestExtractXnMultiplier:
    def test_basic_multiplier(self):
        assert _extract_xn_multiplier("Xtreme Spectacular x6") == 6
        assert _extract_xn_multiplier("Epic Brotherhood x2") == 2

    def test_large_multiplier(self):
        assert _extract_xn_multiplier("Ability x12") == 12

    def test_no_multiplier(self):
        assert _extract_xn_multiplier("Hot Impact") == 0
        assert _extract_xn_multiplier("Re-entry Blast") == 0

    def test_empty_string(self):
        assert _extract_xn_multiplier("") == 0

    def test_case_insensitive(self):
        assert _extract_xn_multiplier("Ability X3") == 3


# ---------------------------------------------------------------------------
# _group_multi_hit_entries tests
# ---------------------------------------------------------------------------


class TestGroupMultiHitEntries:
    def test_empty_list(self):
        assert _group_multi_hit_entries([], 15.0) == []

    def test_single_entry_unchanged(self):
        entries = [{"timestamp": 10.0, "ability_name": "Hit"}]
        result = _group_multi_hit_entries(entries, 15.0)
        assert len(result) == 1
        assert result[0]["ability_name"] == "Hit"
        assert result[0].get("hit_count", 1) == 1
        assert result[0].get("time_range_start") is None

    def test_consecutive_same_name_grouped(self):
        entries = [
            {"timestamp": 197.6, "ability_name": "Re-entry Blast", "damage": 81047},
            {"timestamp": 204.9, "ability_name": "Re-entry Blast", "damage": 81047},
            {"timestamp": 212.2, "ability_name": "Re-entry Blast", "damage": 81047},
            {"timestamp": 219.5, "ability_name": "Re-entry Blast", "damage": 81047},
        ]
        result = _group_multi_hit_entries(entries, 15.0)
        assert len(result) == 1
        assert result[0]["ability_name"] == "Re-entry Blast"
        assert result[0]["hit_count"] == 4
        assert result[0]["time_range_start"] == 197.6
        assert result[0]["time_range_end"] == 219.5

    def test_numbered_suffixes_grouped(self):
        entries = [
            {"timestamp": 30.3, "ability_name": "Flame Floater 1"},
            {"timestamp": 33.5, "ability_name": "Flame Floater 2"},
            {"timestamp": 36.8, "ability_name": "Flame Floater 3"},
            {"timestamp": 39.9, "ability_name": "Flame Floater 4"},
        ]
        result = _group_multi_hit_entries(entries, 15.0)
        assert len(result) == 1
        assert result[0]["ability_name"] == "Flame Floater"
        assert result[0]["hit_count"] == 4
        assert result[0]["time_range_start"] == 30.3
        assert result[0]["time_range_end"] == 39.9

    def test_parenthetical_variants_grouped(self):
        entries = [
            {"timestamp": 160.9, "ability_name": "Xtreme Spectacular"},
            {"timestamp": 168.7, "ability_name": "Xtreme Spectacular (line)"},
            {"timestamp": 173.6, "ability_name": "Xtreme Spectacular (big)"},
        ]
        result = _group_multi_hit_entries(entries, 15.0)
        assert len(result) == 1
        assert result[0]["ability_name"] == "Xtreme Spectacular"
        assert result[0]["hit_count"] == 3

    def test_far_apart_not_grouped(self):
        """Same-name entries more than threshold apart should NOT be grouped."""
        entries = [
            {"timestamp": 14.6, "ability_name": "Hot Impact"},
            {"timestamp": 268.8, "ability_name": "Hot Impact"},
        ]
        result = _group_multi_hit_entries(entries, 15.0)
        assert len(result) == 2
        assert result[0].get("hit_count", 1) == 1
        assert result[1].get("hit_count", 1) == 1

    def test_different_names_not_grouped(self):
        entries = [
            {"timestamp": 10.0, "ability_name": "Ability A"},
            {"timestamp": 12.0, "ability_name": "Ability B"},
        ]
        result = _group_multi_hit_entries(entries, 15.0)
        assert len(result) == 2

    def test_mixed_groups_and_singles(self):
        """Interleaved grouped and single entries."""
        entries = [
            {"timestamp": 30.3, "ability_name": "Flame Floater 1"},
            {"timestamp": 33.5, "ability_name": "Flame Floater 2"},
            {"timestamp": 61.9, "ability_name": "Cutback Blaze 1"},
            {"timestamp": 62.8, "ability_name": "Cutback Blaze 2"},
            {"timestamp": 68.4, "ability_name": "Freaky Pyrotation"},
        ]
        result = _group_multi_hit_entries(entries, 15.0)
        assert len(result) == 3
        assert result[0]["ability_name"] == "Flame Floater"
        assert result[0]["hit_count"] == 2
        assert result[1]["ability_name"] == "Cutback Blaze"
        assert result[1]["hit_count"] == 2
        assert result[2]["ability_name"] == "Freaky Pyrotation"
        assert result[2].get("hit_count", 1) == 1

    def test_preserves_first_entry_data(self):
        """Grouped entry should keep the first entry's damage data."""
        entries = [
            {"timestamp": 30.3, "ability_name": "Flame Floater 1", "unmitigated_damage": 129331.0, "ability_type": "Spread"},
            {"timestamp": 33.5, "ability_name": "Flame Floater 2", "unmitigated_damage": 129331.0, "ability_type": "Spread"},
        ]
        result = _group_multi_hit_entries(entries, 15.0)
        assert len(result) == 1
        assert result[0]["unmitigated_damage"] == 129331.0
        assert result[0]["ability_type"] == "Spread"

    def test_xn_multiplier_in_group(self):
        """Entries with xN suffix should contribute N hits instead of 1."""
        entries = [
            {"timestamp": 160.9, "ability_name": "Xtreme Spectacular"},
            {"timestamp": 169.7, "ability_name": "Xtreme Spectacular x6"},
            {"timestamp": 173.6, "ability_name": "Xtreme Spectacular (big)"},
        ]
        result = _group_multi_hit_entries(entries, 15.0)
        assert len(result) == 1
        assert result[0]["ability_name"] == "Xtreme Spectacular"
        # 1 + 6 + 1 = 8
        assert result[0]["hit_count"] == 8

    def test_single_xn_entry(self):
        """A single entry with xN suffix should have hit_count = N."""
        entries = [{"timestamp": 169.7, "ability_name": "Xtreme Spectacular x6"}]
        result = _group_multi_hit_entries(entries, 15.0)
        assert len(result) == 1
        assert result[0]["hit_count"] == 6


# ---------------------------------------------------------------------------
# _finalize_hit_group tests
# ---------------------------------------------------------------------------


class TestFinalizeHitGroup:
    def test_single_entry_returns_as_is(self):
        entry = {"timestamp": 10.0, "ability_name": "Hit"}
        result = _finalize_hit_group([entry])
        assert result is entry  # same object, not a copy

    def test_single_entry_with_xn_returns_copy(self):
        """An entry with xN suffix should get hit_count set to N."""
        entry = {"timestamp": 10.0, "ability_name": "Epic Brotherhood x2"}
        result = _finalize_hit_group([entry])
        assert result is not entry  # should be a copy
        assert result["hit_count"] == 2

    def test_multi_entry_group(self):
        group = [
            {"timestamp": 10.0, "ability_name": "Blast 1"},
            {"timestamp": 12.0, "ability_name": "Blast 2"},
            {"timestamp": 14.0, "ability_name": "Blast 3"},
        ]
        result = _finalize_hit_group(group)
        assert result["ability_name"] == "Blast"
        assert result["hit_count"] == 3
        assert result["time_range_start"] == 10.0
        assert result["time_range_end"] == 14.0
        assert result["timestamp"] == 10.0

    def test_multi_entry_group_with_xn(self):
        """xN entries in a group should contribute N hits instead of 1."""
        group = [
            {"timestamp": 10.0, "ability_name": "Spectacular"},
            {"timestamp": 11.0, "ability_name": "Spectacular x6"},
        ]
        result = _finalize_hit_group(group)
        assert result["ability_name"] == "Spectacular"
        assert result["hit_count"] == 7  # 1 + 6
        assert result["time_range_start"] == 10.0
        assert result["time_range_end"] == 11.0

