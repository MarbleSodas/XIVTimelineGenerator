from dataclasses import dataclass

def test_encounter_dataclass_is_frozen():
    from fflogs.models import Encounter
    e = Encounter(code="M11S", full_name="AAC Heavyweight M3 (Savage)",
                  boss_name="The Tyrant", zone_id=73,
                  encounter_id=None, expansion="dawntrail", category="savage")
    assert e.code == "M11S"
    assert e.full_name == "AAC Heavyweight M3 (Savage)"
    assert e.encounter_id is None

def test_report_dataclass():
    from fflogs.models import Report
    r = Report(id="abc123", fight_id=1, start_time=1000,
               end_time=2000, kill=True, duration=1000,
               boss_name="The Tyrant", guild_name="TestGuild")
    assert r.id == "abc123"
    assert r.kill is True