"""Data models for XIV Timeline Generator."""

from datetime import datetime
from enum import Enum
from typing import Any


class Expansion(str, Enum):
    """FFXIV Expansion codes."""

    A_REALM_REBORN = "02-arr"
    HEAVENSWARD = "03-hw"
    STORMBLOOD = "04-sb"
    SHADOWBRINGERS = "05-shb"
    ENDWALKER = "06-ew"
    DAWNTRAIL = "07-dt"

    @property
    def display_name(self) -> str:
        """Human-readable expansion name."""
        names = {
            "02-arr": "A Realm Reborn",
            "03-hw": "Heavensward",
            "04-sb": "Stormblood",
            "05-shb": "Shadowbringers",
            "06-ew": "Endwalker",
            "07-dt": "Dawntrail",
        }
        return names.get(self.value, self.value)


class EncounterType(str, Enum):
    """Type of encounter in FFXIV."""

    RAID = "raid"
    TRIAL = "trial"
    DUNGEON = "dungeon"
    ALLIANCE = "alliance"
    ULTIMATE = "ultimate"
    DEEPDUNGEON = "deepdungeon"


class Difficulty(str, Enum):
    """Difficulty level of encounter."""

    NORMAL = "n"
    SAVAGE = "s"
    ULTIMATE = "u"


# Boss name to cactbot file mapping
BOSS_NAME_MAPPING = {
    # Endwalker Raids (Anabaseios)
    "p12s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p11s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p10s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p9s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p8s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p7s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p6s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p5s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p4s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p3s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p2s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "p1s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    # Endwalker Normal Raids
    "p12n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p11n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p10n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p1n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p2n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p3n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p4n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p5n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p6n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p7n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p8n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p9n": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    # Endwalker Trials
    "zodiark": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE},
    "endsinger": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE},
    "barbarricia": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE},
    "herkles": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE},
    "valigarmanda": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE},
    # Dawntrail Raids
    "p10n2": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.NORMAL},
    "p10s2": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    # Shadowbringers Raids
    "e12s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e11s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e10s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e9s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e8s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e7s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e6s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e5s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e4s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e3s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e2s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    "e1s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE},
    # Ultimate
    "tea": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE},
    "ubc": {"expansion": Expansion.ENDWALKER, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE},
    "top": {"expansion": Expansion.ENDWALKER, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE},
}


def resolve_boss_name(boss_name: str) -> dict[str, Any] | None:
    """Resolve boss name to cactbot file parameters."""
    # Direct lowercase match
    normalized = boss_name.lower().strip()
    if normalized in BOSS_NAME_MAPPING:
        return BOSS_NAME_MAPPING[normalized]

    # Try partial match
    for key, value in BOSS_NAME_MAPPING.items():
        if key in normalized or normalized in key:
            return value

    return None
