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
# Keys are user-friendly boss names (M#S format for current raids)
# Values map to cactbot file names (raid codes like r8s, p12s, etc.)
BOSS_NAME_MAPPING = {
    # ============ Dawntrail (07-dt) - The Arcadion ============
    # AAC Light-heavyweight Tier (r1s-r4s = M1S-M4S)
    "m1s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r1s"},
    "m2s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r2s"},
    "m3s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r3s"},
    "m4s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r4s"},
    # AAC Cruiserweight Tier (r5s-r8s = M5S-M8S)
    "m5s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r5s"},
    "m6s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r6s"},
    "m7s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r7s"},
    "m8s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r8s"},
    # AAC Heavyweight Tier (r9s-r12s = M9S-M12S)
    "m9s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r9s"},
    "m10s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r10s"},
    "m11s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r11s"},
    "m12s": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "r12s"},
    
    # Dawntrail Trials
    "zoraal_ja": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "zoraal-ja"},
    "arkveld": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "arkveld"},
    "doomtrain": {"expansion": Expansion.DAWNTRAIL, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "doomtrain"},
    
    # ============ Endwalker (06-ew) - Pandæmonium ============
    # Asphodelos (p1s-p4s)
    "p1s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p1s"},
    "p2s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p2s"},
    "p3s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p3s"},
    "p4s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p4s"},
    # Abyssos (p5s-p8s)
    "p5s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p5s"},
    "p6s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p6s"},
    "p7s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p7s"},
    "p8s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p8s"},
    # Anabaseios (p9s-p12s)
    "p9s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p9s"},
    "p10s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p10s"},
    "p11s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p11s"},
    "p12s": {"expansion": Expansion.ENDWALKER, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "p12s"},
    
    # Endwalker Trials
    "zodiark": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "zodiark"},
    "endsinger": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "endsinger"},
    "barbariccia": {"expansion": Expansion.ENDWALKER, "type": EncounterType.TRIAL, "difficulty": Difficulty.SAVAGE, "cactbot_id": "barbariccia"},
    
    # Endwalker Ultimates
    "omega_protocol": {"expansion": Expansion.ENDWALKER, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "the_omega_protocol"},
    "top": {"expansion": Expansion.ENDWALKER, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "the_omega_protocol"},
    "dsr": {"expansion": Expansion.ENDWALKER, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "dragonsongs_reprise_ultimate"},
    "dragonsongs_reprise": {"expansion": Expansion.ENDWALKER, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "dragonsongs_reprise_ultimate"},
    
    # ============ Shadowbringers (05-shb) - Eden ============
    # Eden's Promise (e1s-e12s)
    "e1s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e1s"},
    "e2s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e2s"},
    "e3s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e3s"},
    "e4s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e4s"},
    "e5s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e5s"},
    "e6s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e6s"},
    "e7s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e7s"},
    "e8s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e8s"},
    "e9s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e9s"},
    "e10s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e10s"},
    "e11s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e11s"},
    "e12s": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "e12s"},
    
    # Shadowbringers Ultimates
    "tea": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "tea"},
    "ultima_unreal": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "uco_ultimate"},
    "uco": {"expansion": Expansion.SHADOWBRINGERS, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "uco_ultimate"},
    
    # ============ Stormblood (04-sb) - Omega ============
    # Omega Deltascape (o1s-o4s)
    "o1s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o1s"},
    "o2s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o2s"},
    "o3s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o3s"},
    "o4s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o4s"},
    # Omega Sigmascape (o5s-o8s)
    "o5s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o5s"},
    "o6s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o6s"},
    "o7s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o7s"},
    "o8s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o8s"},
    # Omega Omegascape (o9s-o12s)
    "o9s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o9s"},
    "o10s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o10s"},
    "o11s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o11s"},
    "o12s": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "o12s"},
    
    # Stormblood Ultimates
    "uwu": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "ultimate"},
    "ultima_weapon": {"expansion": Expansion.STORMBLOOD, "type": EncounterType.ULTIMATE, "difficulty": Difficulty.ULTIMATE, "cactbot_id": "ultimate"},
    
    # ============ Heavensward (03-hw) - Alexander ============
    # Alexander (a1s-a12s)
    "a1s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a1s"},
    "a2s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a2s"},
    "a3s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a3s"},
    "a4s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a4s"},
    "a5s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a5s"},
    "a6s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a6s"},
    "a7s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a7s"},
    "a8s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a8s"},
    "a9s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a9s"},
    "a10s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a10s"},
    "a11s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a11s"},
    "a12s": {"expansion": Expansion.HEAVENSWARD, "type": EncounterType.RAID, "difficulty": Difficulty.SAVAGE, "cactbot_id": "a12s"},
}


def resolve_boss_name(boss_name: str) -> dict[str, Any] | None:
    """Resolve boss name to cactbot file parameters."""
    # Normalize: replace spaces/hyphens with underscores and lowercase
    normalized = boss_name.lower().strip().replace(" ", "_").replace("-", "_")
    if normalized in BOSS_NAME_MAPPING:
        return BOSS_NAME_MAPPING[normalized]

    # Try partial match
    for key, value in BOSS_NAME_MAPPING.items():
        if key in normalized or normalized in key:
            return value

    return None


class AbilityType(str, Enum):
    """Type of boss ability based on player impact."""

    # Direct damage to players
    TANK_BUSTER = "tankbuster"
    DUAL_TANK_BUSTER = "dual_tankbuster"
    RAIDWIDE = "raidwide"
    SMALL_PARTY = "small_party"
    PAIR = "pair"
    SHARE = "share"
    STACK = "stack"
    
    # AoE mechanics
    AOE = "aoe"
    CONE = "cone"
    DONUT = "donut"
    LINE = "line"
    
    # Movement/mechanic
    KNOCKBACK = "knockback"
    PULL = "pull"
    TETHER = "tether"
    PROTEAN = "protean"
    
    # Debuffs/buffs
    DEBUFF = "debuff"
    BUFF = "buff"
    
    # Phase transitions
    PHASE_CHANGE = "phase_change"
    ENRAGE = "enrage"
    
    # Untargeted/utility
    BUFF_SELF = "buff_self"
    SUMMON = "summon"
    UNTARGETED = "untargeted"


# Abilities that always hit players
ALWAYS_PLAYER_HIT_PATTERNS = [
    "tank", "buster", "raidwide", "aoe", "cone", "line", "flare",
    "thunder", "meteor", "quake", "doom", "death", "enrage",
    "attack", "strike", "slash", "claw", "fang", "tail",
    "beam", "laser", "cleave", "breath", "gaze", "pulse",
    "eruption", "explosion", "wave", "nova", "burst",
    "knockback", "pull", "tether", "stack", "share",
    "debuff", "vuln", "bleed", "poison", "curse",
    "phase", "enrage", "ultimate", "inferno", "firestorm",
    "fire", "ice", "blizzard", "water", "stone", "aero",
    "holy", "firaga", "thundaga", "blizzaga", "waterga",
    "stonega", "aeroga", "void", "dark", "umbra", "astral",
    "void", "sacrifice", "annihil", "obliterate",
    "mega", "ultra", "giga", "hyper", "pan", "exat", "tetrad",
    "octo", "hexa", "penta", "quad", "chariot", "dynamo",
    "sword", "axe", "hammer", "wing", "horn",
    "screw", "propeller", "gear", "clock", "watch",
    "plume", "feather", "talon", "beak", "roar", "howl",
    "screech", "shriek", "glower", "stare", "glare",
    "sweep", "swipe", "smash", "crush", "bash", "pummel",
    "lariat", "headbutt", "kick", "punch", "slap",
]


# Abilities that don't hit players
NEVER_PLAYER_HIT_PATTERNS = [
    "sync", "reset", "ready", "waiting", "combat", "incombat",
    "targetable", "untargetable", "death", "respawn", "wipe",
    "limit break", "lb", "gauge", "check",
    "start", "end", "begin", "init", "setup",
    "self", "buff", "embrace", "protect", "shield",
    "spawn", "summon", "add", "minion", "call", "conjure",
]


def classify_ability(ability_name: str) -> AbilityType | None:
    """Classify a boss ability based on its name."""
    name_lower = ability_name.lower()
    
    # Check if it NEVER hits players
    for pattern in NEVER_PLAYER_HIT_PATTERNS:
        if pattern in name_lower:
            is_definite_hit = any(p in name_lower for p in ["tank", "buster", "raidwide", "aoe", "thunder", "flare", "meteor", "doom", "enrage"])
            if not is_definite_hit:
                return None
    
    # Check for phase change/enrage
    for pattern in ["enrage", "limit break", "final", "victory"]:
        if pattern in name_lower:
            return AbilityType.ENRAGE
    
    # Check for phase change
    for pattern in ["phase", "transition"]:
        if pattern in name_lower:
            return AbilityType.PHASE_CHANGE
    
    # Check dual tank buster first
    if any(kw in name_lower for kw in ["dual", "double", "twin", "both"]) and "tank" in name_lower:
        return AbilityType.DUAL_TANK_BUSTER
    
    # Check tank buster
    if any(kw in name_lower for kw in ["tank", "buster", "tb", "tether", "single"]):
        return AbilityType.TANK_BUSTER
    
    # Check raidwide
    if any(kw in name_lower for kw in ["raidwide", "raid wide", "party-wide", "everyone", "all", "mega", "ultra", "giga", "hyper", "pan", "exat", "tetrad", "octo", "quad", "hexa", "penta"]):
        return AbilityType.RAIDWIDE
    
    # Check pair
    if any(kw in name_lower for kw in ["pair", "two", "2", "couple", "twins", "spread", "both", "duo", "binary"]):
        return AbilityType.PAIR
    
    # Check share
    if any(kw in name_lower for kw in ["share", "shared", "lightning", "thunder"]):
        return AbilityType.SHARE
    
    # Check stack
    if any(kw in name_lower for kw in ["stack", "together", "group up", "combine", "group"]) and "spread" not in name_lower:
        return AbilityType.STACK
    
    # Check AoE types
    if any(kw in name_lower for kw in ["cone", "frontal", "front", "cleave", "breath", "gaze", "beam", "laser", "sweep", "tail", "swipe"]):
        return AbilityType.CONE
    
    if any(kw in name_lower for kw in ["donut", "ring", "orbit", "around", "surround", "outer", "hollow"]):
        return AbilityType.DONUT
    
    if any(kw in name_lower for kw in ["line", "straight", "width", "ray", "slash", "rectangle", "cross", "plus"]):
        return AbilityType.LINE
    
    # Check knockback
    if any(kw in name_lower for kw in ["knockback", "knock back", "push", "repulsion", "blast", "shockwave", "wind", "blow", "launch"]):
        return AbilityType.KNOCKBACK
    
    # Check pull
    if any(kw in name_lower for kw in ["pull", "attract", "gravity", "singularity", "black hole", "hole", "absorb"]):
        return AbilityType.PULL
    
    # Check tether
    if any(kw in name_lower for kw in ["tether", "link", "chain", "bond", "connection"]):
        return AbilityType.TETHER
    
    # Check protean
    if any(kw in name_lower for kw in ["protean", "wave", "cardinal", "ordinal"]):
        return AbilityType.PROTEAN
    
    # Check debuff
    if any(kw in name_lower for kw in ["debuff", "bleed", "poison", "disease", "curse", "doom", "slow", "stun", "sleep", "bind", "silence", "blind", "vuln", "vulnerability", "weakness"]):
        return AbilityType.DEBUFF
    
    # Check AoE general
    if any(kw in name_lower for kw in ["aoe", "area", "circle", "radius", "burst", "explosion", "pulse", "wave", "eruption", "detonate", "nova", "flare", "firestorm", "inferno", "thunder", "blizzard", "flood", "tsunami", "meteor", "quake", "tremor", "fire", "ice", "holy", "water", "stone", "aero", "void", "dark"]):
        return AbilityType.AOE
    
    # Default to AoE if it looks like an attack
    if any(kw in name_lower for kw in ALWAYS_PLAYER_HIT_PATTERNS):
        return AbilityType.AOE
    
    return None


def hits_players(ability_name: str) -> bool:
    """Determine if a boss ability hits players."""
    name_lower = ability_name.lower()
    
    # Check if it's definitely NOT player-targeted
    for pattern in NEVER_PLAYER_HIT_PATTERNS:
        if pattern in name_lower:
            override = any(o in name_lower for o in ["tank", "buster", "raidwide", "thunder", "flare", "meteor", "doom", "aoe", "enrage", "attack", "strike"])
            if not override:
                return False
    
    # Check if it definitely hits players
    for pattern in ALWAYS_PLAYER_HIT_PATTERNS:
        if pattern in name_lower:
            return True
    
    # Check for common attack patterns
    attack_indicators = [
        "attack", "strike", "slash", "thrust", "claw", "fang", 
        "tail", "bite", "smash", "crush", "blast", "burn",
        "shoot", "fire", "ice", "thunder", "wind", "earth",
        "water", "holy", "dark", "void", "poison", "blind",
    ]
    
    if any(ind in name_lower for ind in attack_indicators):
        return True
    
    return False


class TargetType(str, Enum):
    """Target type for boss abilities."""
    
    TANK = "tank"
    HEALER = "healer"
    DPS = "dps"
    ANY = "any"
    UNKNOWN = "unknown"


def infer_target_type(ability_name: str) -> TargetType | None:
    """Infer the target type of a boss ability."""
    name_lower = ability_name.lower()
    
    # Check for tank-targeted abilities
    if any(kw in name_lower for kw in ["tank", "buster", "tether"]):
        return TargetType.TANK
    
    # Check for healer-targeted abilities
    if any(kw in name_lower for kw in ["heal", "regen", "remedy", "cure"]):
        return TargetType.HEALER
    
    # Check for DPS-targeted abilities
    if any(kw in name_lower for kw in ["dps", "magic", "physical", "ranged", "melee"]):
        return TargetType.DPS
    
    # Default to ANY for raid-wide or untargeted
    if any(kw in name_lower for kw in ["raidwide", "aoe", "everyone", "all", "party"]):
        return TargetType.ANY
    
    return TargetType.UNKNOWN

# Configuration constants
MULTI_HIT_TIME_THRESHOLD = 0.5  # seconds - abilities within this threshold are considered multi-hit
