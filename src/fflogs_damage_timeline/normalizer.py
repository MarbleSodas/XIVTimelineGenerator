"""Normalization helpers for structured FF Logs damage timelines."""

from typing import Any

from fflogs_damage_timeline.filters import (
    build_ability_map,
    build_actor_map,
    filter_damage_events,
)


def format_timestamp(timestamp_ms: float) -> str:
    total_ms = max(0, int(round(timestamp_ms)))
    minutes, remainder = divmod(total_ms, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def parse_buff_ids(raw_buffs: Any) -> list[int]:
    if not raw_buffs or not isinstance(raw_buffs, str):
        return []

    buff_ids: list[int] = []
    for chunk in raw_buffs.split("."):
        if not chunk:
            continue
        try:
            buff_ids.append(int(chunk))
        except ValueError:
            continue
    return buff_ids


def categorize_event_type(event_type: str | None) -> str:
    if event_type == "calculateddamage":
        return "prepare"
    if event_type == "damage":
        return "damage"
    return "other"


def summarize_actor(actor_id: Any, actors: dict[int, dict[str, Any]]) -> dict[str, Any]:
    if actor_id is None:
        return {
            "id": None,
            "game_id": None,
            "name": None,
            "type": None,
            "sub_type": None,
            "server": None,
            "pet_owner_id": None,
        }

    actor = actors.get(int(actor_id)) or {}
    return {
        "id": int(actor_id),
        "game_id": actor.get("gameID"),
        "name": actor.get("name"),
        "type": actor.get("type"),
        "sub_type": actor.get("subType"),
        "server": actor.get("server"),
        "pet_owner_id": actor.get("petOwner"),
    }


def summarize_ability(
    ability_game_id: Any,
    abilities: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    if ability_game_id is None:
        return {
            "game_id": None,
            "name": None,
            "type": None,
            "is_auto_attack": False,
        }

    ability = abilities.get(int(ability_game_id)) or {}
    ability_name = ability.get("name")
    return {
        "game_id": int(ability_game_id),
        "name": ability_name,
        "type": ability.get("type"),
        "is_auto_attack": ability_name == "Attack",
    }


def normalize_event(
    event: dict[str, Any],
    fight_start_time: float,
    actors: dict[int, dict[str, Any]],
    abilities: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    timestamp_ms = float(event["timestamp"]) - float(fight_start_time)
    amount = event.get("amount")
    unmitigated_amount = event.get("unmitigatedAmount")
    reduction_amount = None
    reduction_percent = None

    if (
        isinstance(amount, (int, float))
        and isinstance(unmitigated_amount, (int, float))
        and unmitigated_amount > 0
    ):
        reduction_amount = max(unmitigated_amount - amount, 0)
        reduction_percent = round((reduction_amount / unmitigated_amount) * 100, 2)

    return {
        "timestamp_ms": int(round(timestamp_ms)),
        "timestamp": format_timestamp(timestamp_ms),
        "event_type": event.get("type"),
        "category": categorize_event_type(event.get("type")),
        "packet_id": event.get("packetID"),
        "fight_id": event.get("fight"),
        "source": summarize_actor(event.get("sourceID"), actors),
        "target": summarize_actor(event.get("targetID"), actors),
        "ability": summarize_ability(event.get("abilityGameID"), abilities),
        "damage": {
            "amount": amount,
            "unmitigated_amount": unmitigated_amount,
            "absorbed": event.get("absorbed", 0),
            "blocked": event.get("blocked", 0),
            "mitigated": event.get("mitigated", 0),
            "overkill": event.get("overkill", 0),
            "reduction_amount": reduction_amount,
            "reduction_percent": reduction_percent,
            "multiplier": event.get("multiplier"),
        },
        "hit_type": event.get("hitType"),
        "tick": bool(event.get("tick")),
        "buff_ids": parse_buff_ids(event.get("buffs")),
    }


def include_event_in_timeline(event: dict[str, Any]) -> bool:
    if event.get("category") == "prepare":
        return False
    ability = event.get("ability") or {}
    if ability.get("is_auto_attack"):
        return False
    return True


def normalize_fight_timeline(
    fight: dict[str, Any],
    report_start_time: float,
    events: list[dict[str, Any]],
    actors: list[dict[str, Any]],
    abilities: list[dict[str, Any]],
) -> dict[str, Any]:
    actor_map = build_actor_map(actors)
    ability_map = build_ability_map(abilities)
    filtered_events = filter_damage_events(
        events,
        actor_map,
        fight.get("friendlyPlayers"),
    )
    normalized_events = [
        normalize_event(event, fight["startTime"], actor_map, ability_map)
        for event in filtered_events
    ]
    timeline_events = [
        event for event in normalized_events if include_event_in_timeline(event)
    ]

    return {
        "fight_id": fight["id"],
        "name": fight.get("name"),
        "encounter_id": fight.get("encounterID"),
        "difficulty": fight.get("difficulty"),
        "kill": fight.get("kill", True),
        "start_time_relative_ms": fight["startTime"],
        "end_time_relative_ms": fight["endTime"],
        "start_time_absolute_ms": int(report_start_time + fight["startTime"]),
        "end_time_absolute_ms": int(report_start_time + fight["endTime"]),
        "duration_ms": int(fight["endTime"] - fight["startTime"]),
        "friendly_player_ids": list(fight.get("friendlyPlayers") or []),
        "event_count": len(timeline_events),
        "events": timeline_events,
    }
