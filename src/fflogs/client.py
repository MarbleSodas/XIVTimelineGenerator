from typing import Optional
from .cache import CacheManager
from .auth import AuthManager
from .encounters import EncounterLoader, Encounter
from .models import Report
from fflogsapi import FFLogsClient as _FFLogsClient

DEFAULT_CLIENT_ID = "a14508fc-5d09-418f-a1db-01879a8eaf14"
DEFAULT_CLIENT_SECRET = "Q9YZmTib56VT6AGNhuQQ2iPDJiFLVYFiMLYmsQN9"

class FFLogsClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ):
        self._cache_dir = cache_dir
        self._cache = CacheManager(cache_dir=cache_dir) if cache_dir else CacheManager()
        self._auth = AuthManager(
            client_id=client_id or DEFAULT_CLIENT_ID,
            client_secret=client_secret or DEFAULT_CLIENT_SECRET,
            cache=self._cache,
        )
        self._loader = EncounterLoader()
        self._client: Optional[_FFLogsClient] = None

    def _get_client(self) -> _FFLogsClient:
        if self._client is None:
            token = self._auth.get_token()
            self._client = _FFLogsClient(token)
        return self._client

    def resolve_encounter_id(self, encounter: Encounter) -> int:
        """Resolve encounter_id from API if not cached, then cache it."""
        ids = self._cache.load_encounter_ids()
        if encounter.code in ids:
            return ids[encounter.code]

        client = self._get_client()
        zone = client.get_zone(encounter.zone_id)
        for enc in zone.encounters():
            ids[enc.name] = enc.id
            # Also map by boss name for fuzzy matching
            ids[encounter.boss_name] = enc.id

        if encounter.full_name in ids:
            ids[encounter.code] = ids[encounter.full_name]
        elif encounter.boss_name in ids:
            ids[encounter.code] = ids[encounter.boss_name]

        self._cache.save_encounter_ids(ids)
        return ids.get(encounter.code, 0)

    def get_reports(self, encounter: Encounter, limit: int = 30) -> list[Report]:
        """Fetch `limit` recent kill reports for the given encounter."""
        encounter_id = self.resolve_encounter_id(encounter)
        client = self._get_client()

        reports = list(client.reports(
            zone=encounter.zone_id,
            boss=encounter_id,
            difficulty=101,  # Savage
            limit=limit,
        ))

        results: list[Report] = []
        for r in reports:
            for fight in r.fights():
                if fight.encounter() == encounter_id and fight.is_kill():
                    results.append(Report(
                        id=r.code,
                        fight_id=fight.id,
                        start_time=r.start_time(),
                        end_time=r.end_time(),
                        kill=True,
                        duration=fight.duration(),
                        boss_name=encounter.boss_name,
                        guild_name=getattr(r, 'guild', lambda: None)(),
                    ))
                    break
            if len(results) >= limit:
                break

        return results[:limit]
