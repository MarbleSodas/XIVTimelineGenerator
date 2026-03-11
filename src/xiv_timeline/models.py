"""Data models for XIV Timeline Generator."""

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


# ---------------------------------------------------------------------------
# Boss name → cactbot file mapping
# ---------------------------------------------------------------------------

BOSS_NAME_MAPPING: dict[str, dict[str, Any]] = {
    # ============ Dawntrail (07-dt) - The Arcadion ============
    # AAC Light-heavyweight (M1S-M4S → r1s-r4s)
    "m1s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r1s", "fflogs_id": 93},
    "m2s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r2s", "fflogs_id": 94},
    "m3s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r3s", "fflogs_id": 95},
    "m4s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r4s", "fflogs_id": 96},
    # AAC Cruiserweight (M5S-M8S → r5s-r8s)
    "m5s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r5s", "fflogs_id": 97},
    "m6s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r6s", "fflogs_id": 98},
    "m7s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r7s", "fflogs_id": 99},
    "m8s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r8s", "fflogs_id": 100},
    # AAC Heavyweight (M9S-M12S → r9s-r12s)
    "m9s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r9s", "fflogs_id": 101},
    "m10s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r10s", "fflogs_id": 102},
    "m11s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r11s", "fflogs_id": 103},
    "m12s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r12s", "fflogs_id": 104},
    # Dawntrail Trials
    "zoraal_ja": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "zoraal-ja", "fflogs_id": 1072},
    "arkveld": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "arkveld", "fflogs_id": 1082},
    "doomtrain": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "doomtrain", "fflogs_id": 1083},

    # ============ Endwalker (06-ew) - Pandæmonium ============
    # Asphodelos (P1S-P4S)
    "p1s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p1s", "fflogs_id": 78},
    "p2s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p2s", "fflogs_id": 79},
    "p3s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p3s", "fflogs_id": 80},
    "p4s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p4s", "fflogs_id": 81},
    # Abyssos (P5S-P8S)
    "p5s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p5s", "fflogs_id": 83},
    "p6s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p6s", "fflogs_id": 84},
    "p7s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p7s", "fflogs_id": 85},
    "p8s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p8s", "fflogs_id": 86},
    # Anabaseios (P9S-P12S)
    "p9s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p9s", "fflogs_id": 88},
    "p10s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p10s", "fflogs_id": 89},
    "p11s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p11s", "fflogs_id": 90},
    "p12s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p12s", "fflogs_id": 91},
    # Endwalker Trials
    "zodiark": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "zodiark", "fflogs_id": 1058},
    "endsinger": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "endsinger", "fflogs_id": 1063},
    "barbariccia": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "barbariccia", "fflogs_id": 1066},
    # Endwalker Ultimates
    "omega_protocol": {"expansion": Expansion.ENDWALKER, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "the_omega_protocol", "fflogs_id": 1077},
    "top": {"expansion": Expansion.ENDWALKER, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "the_omega_protocol", "fflogs_id": 1077},
    "dsr": {"expansion": Expansion.ENDWALKER, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "dragonsongs_reprise_ultimate", "fflogs_id": 1076},
    "dragonsongs_reprise": {"expansion": Expansion.ENDWALKER, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "dragonsongs_reprise_ultimate", "fflogs_id": 1076},

    # ============ Shadowbringers (05-shb) - Eden ============
    # Eden's Gate (E1S-E4S)
    "e1s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e1s", "fflogs_id": 65},
    "e2s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e2s", "fflogs_id": 66},
    "e3s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e3s", "fflogs_id": 67},
    "e4s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e4s", "fflogs_id": 68},
    # Eden's Verse (E5S-E8S)
    "e5s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e5s", "fflogs_id": 69},
    "e6s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e6s", "fflogs_id": 70},
    "e7s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e7s", "fflogs_id": 71},
    "e8s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e8s", "fflogs_id": 72},
    # Eden's Promise (E9S-E12S)
    "e9s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e9s", "fflogs_id": 73},
    "e10s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e10s", "fflogs_id": 74},
    "e11s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e11s", "fflogs_id": 75},
    "e12s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e12s", "fflogs_id": 76},
    # Shadowbringers Ultimates
    "tea": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "tea", "fflogs_id": 1075},
    "ultima_unreal": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "uco_ultimate", "fflogs_id": 1073},
    "uco": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "uco_ultimate", "fflogs_id": 1073},

    # ============ Stormblood (04-sb) - Omega ============
    # Deltascape (O1S-O4S)
    "o1s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o1s", "fflogs_id": 42},
    "o2s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o2s", "fflogs_id": 43},
    "o3s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o3s", "fflogs_id": 44},
    "o4s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o4s", "fflogs_id": 45},
    # Sigmascape (O5S-O8S)
    "o5s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o5s", "fflogs_id": 51},
    "o6s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o6s", "fflogs_id": 52},
    "o7s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o7s", "fflogs_id": 53},
    "o8s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o8s", "fflogs_id": 54},
    # Alphascape (O9S-O12S)
    "o9s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o9s", "fflogs_id": 60},
    "o10s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o10s", "fflogs_id": 61},
    "o11s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o11s", "fflogs_id": 62},
    "o12s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o12s", "fflogs_id": 63},
    # Stormblood Ultimates
    "uwu": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "ultimate", "fflogs_id": 1074},
    "ultima_weapon": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "ultimate", "fflogs_id": 1074},

    # ============ Heavensward (03-hw) - Alexander ============
    # Gordias (A1S-A4S)
    "a1s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a1s", "fflogs_id": 18},
    "a2s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a2s", "fflogs_id": 19},
    "a3s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a3s", "fflogs_id": 20},
    "a4s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a4s", "fflogs_id": 21},
    # Midas (A5S-A8S)
    "a5s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a5s", "fflogs_id": 26},
    "a6s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a6s", "fflogs_id": 27},
    "a7s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a7s", "fflogs_id": 28},
    "a8s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a8s", "fflogs_id": 29},
    # The Creator (A9S-A12S)
    "a9s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a9s", "fflogs_id": 34},
    "a10s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a10s", "fflogs_id": 35},
    "a11s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a11s", "fflogs_id": 36},
    "a12s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a12s", "fflogs_id": 37},
}


def resolve_boss_name(boss_name: str) -> dict[str, Any] | None:
    """Resolve a user-provided boss name to cactbot file parameters.

    Tries exact match first, then partial match on both sides.
    """
    normalized = boss_name.lower().strip().replace(" ", "_").replace("-", "_")

    if normalized in BOSS_NAME_MAPPING:
        return BOSS_NAME_MAPPING[normalized]

    # Partial match fallback
    for key, value in BOSS_NAME_MAPPING.items():
        if key in normalized or normalized in key:
            return value

    return None


# Grouping threshold — abilities within this window count as multi-hit
MULTI_HIT_TIME_THRESHOLD = 0.5  # seconds

# Grouping threshold for the final synthesized timeline output.
# Consecutive same-name abilities within this window are consolidated.
MULTI_HIT_GROUP_THRESHOLD = 15.0  # seconds
