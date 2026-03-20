"""Event filters for FF Logs damage timeline."""

from typing import TypedDict

# Constants
AUTO_ATTACK_THRESHOLD = 100  # abilityGameID below this is auto-attack
HIT_TYPE_MISS = 1  # hitType == 1 means the attack missed


class Actor(TypedDict):
    """Actor structure from FF Logs combat data."""
    id: int
    name: str
    subType: str
    type: str


class Event(TypedDict):
    """Event structure from FF Logs."""
    timestamp: int
    targetID: int
    sourceID: int
    abilityGameID: int
    hitType: int
    amount: int


def filter_hit_success(event: Event) -> bool:
    """Return True if the event is not a miss (hitType != 1)."""
    return event.get("hitType", 0) != HIT_TYPE_MISS


def filter_non_auto_attack(event: Event) -> bool:
    """Return True if the event is not an auto-attack (abilityGameID >= 100)."""
    return event.get("abilityGameID", 0) >= AUTO_ATTACK_THRESHOLD


def filter_player_targets(event: Event, actors: dict[int, Actor]) -> bool:
    """Return True if the target's subType is 'Player'."""
    target_id = event.get("targetID")
    if target_id is None:
        return False
    actor = actors.get(target_id)
    if actor is None:
        return False
    return actor.get("subType") == "Player"


def filter_damage_events(events: list[Event], actors: dict[int, Actor]) -> list[Event]:
    """Apply all filters and return a new filtered list of events."""
    result = []
    for event in events:
        if filter_hit_success(event):
            if filter_non_auto_attack(event):
                if filter_player_targets(event, actors):
                    result.append(event)
    return result
