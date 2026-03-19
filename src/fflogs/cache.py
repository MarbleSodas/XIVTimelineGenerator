import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

DEFAULT_CACHE_DIR = Path.home() / ".xivtimelinegenerator"


class CacheManager:
    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR):
        self.cache_dir = cache_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._token_file = self.cache_dir / "token.json"
        self._encounter_file = self.cache_dir / "encounters.json"

    # --- Token ---
    def load_token(self) -> Optional[str]:
        if not self._token_file.exists():
            return None
        data = json.loads(self._token_file.read_text())
        expiry = datetime.fromisoformat(data["expires_at"])
        if datetime.now(timezone.utc) >= expiry:
            self._token_file.unlink()
            return None
        return data["access_token"]

    def save_token(self, access_token: str, expires_in: int):
        expires_at = datetime.now(timezone.utc).timestamp() + expires_in
        self._token_file.write_text(json.dumps({
            "access_token": access_token,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
        }))

    # --- Encounter IDs ---
    def load_encounter_ids(self) -> dict[str, int]:
        if not self._encounter_file.exists():
            return {}
        return json.loads(self._encounter_file.read_text())

    def save_encounter_ids(self, ids: dict[str, int]):
        self._encounter_file.write_text(json.dumps(ids))
