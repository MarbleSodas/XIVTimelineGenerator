"""Tests for the data models."""

import pytest
from xiv_timeline.models import resolve_boss_name, Expansion


def test_resolve_boss_name_exact():
    result = resolve_boss_name("p12s")
    assert result is not None
    assert result["expansion"] == Expansion.ENDWALKER
    assert result["cactbot_id"] == "p12s"


def test_resolve_boss_name_case_insensitive():
    result = resolve_boss_name("P12S")
    assert result is not None
    assert result["cactbot_id"] == "p12s"


def test_resolve_boss_name_unknown():
    assert resolve_boss_name("not_a_boss") is None


def test_resolve_boss_name_partial():
    result = resolve_boss_name("m10")
    assert result is not None
    assert result["cactbot_id"] == "r10s"
