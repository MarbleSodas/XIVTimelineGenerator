from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class Encounter:
    code: str
    full_name: str
    boss_name: str
    zone_id: int
    encounter_id: Optional[int]
    expansion: str
    category: str  # "savage" | "ultimate"

@dataclass(frozen=True)
class Report:
    id: str           # FFLogs report code (e.g., "H12n3gyQWwx98KLN")
    fight_id: int
    start_time: int  # unix ms
    end_time: int
    kill: bool
    duration: int    # ms
    boss_name: str
    guild_name: Optional[str]

    @property
    def date(self) -> datetime:
        return datetime.fromtimestamp(self.start_time / 1000)