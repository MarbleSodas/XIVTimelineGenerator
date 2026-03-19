from pathlib import Path

def test_load_dawntrail_yaml():
    from fflogs.encounters import EncounterLoader
    loader = EncounterLoader(data_dir=Path("data/encounters"))
    encounters = loader.load_expansion("dawntrail")
    assert len(encounters) > 0
    m11s = next(e for e in encounters if e.code == "M11S")
    assert m11s.full_name == "AAC Heavyweight M3 (Savage)"
    assert m11s.boss_name == "The Tyrant"
    assert m11s.zone_id == 73

def test_get_by_code():
    from fflogs.encounters import EncounterLoader
    loader = EncounterLoader(data_dir=Path("data/encounters"))
    e = loader.get_by_code("FRU")
    assert e.code == "FRU"
    assert e.full_name == "Futures Rewritten (Ultimate)"
