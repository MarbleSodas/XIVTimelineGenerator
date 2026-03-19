import tempfile
from pathlib import Path


def test_cache_dir_creation():
    from fflogs.cache import CacheManager
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(cache_dir=Path(tmpdir))
        assert (Path(tmpdir) / "cache").exists()


def test_token_caching():
    from fflogs.cache import CacheManager
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(cache_dir=Path(tmpdir))
        cm.save_token("test_token", expires_in=3600)
        loaded = cm.load_token()
        assert loaded == "test_token"


def test_encounter_ids_caching():
    from fflogs.cache import CacheManager
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(cache_dir=Path(tmpdir))
        ids = {"M11S": 1234, "TOP": 5678}
        cm.save_encounter_ids(ids)
        loaded = cm.load_encounter_ids()
        assert loaded == ids