import os
import tempfile
from pathlib import Path

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
