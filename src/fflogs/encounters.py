import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class Encounter:
    code: str
    full_name: str
    boss_name: str
    zone_id: int
    encounter_id: Optional[int]
    expansion: str
    category: str  # "savage" | "ultimate"


@dataclass
class Tier:
    name: str
    short_name: str
    zone_id: int
    encounters: list[Encounter]


@dataclass
class ExpansionData:
    expansion: str
    tiers: list[Tier]
    ultimates: list[Encounter]


class EncounterLoader:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path(__file__).parent.parent.parent.parent / "data" / "encounters"

    def load_expansion(self, expansion: str) -> list[Encounter]:
        yaml_path = self.data_dir / f"{expansion}.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        encounters: list[Encounter] = []
        for tier in data.get("tiers", []):
            for enc in tier["encounters"]:
                encounters.append(Encounter(
                    code=enc["code"],
                    full_name=enc["full_name"],
                    boss_name=enc["boss_name"],
                    zone_id=tier["zone_id"],
                    encounter_id=enc.get("encounter_id"),
                    expansion=expansion,
                    category="savage",
                ))

        for ult in data.get("ultimates", []):
            encounters.append(Encounter(
                code=ult["code"],
                full_name=ult["full_name"],
                boss_name=ult.get("boss_name", ult["full_name"].split("(")[0].strip()),
                zone_id=ult["zone_id"],
                encounter_id=ult.get("encounter_id"),
                expansion=expansion,
                category="ultimate",
            ))

        return encounters

    def get_by_code(self, code: str) -> Optional[Encounter]:
        for exp in ["dawntrail", "endwalker", "shadowbringers", "stormblood"]:
            for enc in self.load_expansion(exp):
                if enc.code == code:
                    return enc
        return None

    def all_encounters(self) -> list[Encounter]:
        all_enc = []
        for exp in ["dawntrail", "endwalker", "shadowbringers", "stormblood"]:
            all_enc.extend(self.load_expansion(exp))
        return all_enc
