"""Helpers for selecting player-targeted FF Logs damage events."""

from typing import Any


def build_actor_map(actors: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Index report actors by their report-local actor ID."""
    return {
        int(actor["id"]): actor
        for actor in actors
        if actor.get("id") is not None
    }


def build_ability_map(abilities: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Index report abilities by their game ID."""
    return {
        int(ability["gameID"]): ability
        for ability in abilities
        if ability.get("gameID") is not None
    }


def filter_damage_events(
    events: list[dict[str, Any]],
    actors: dict[int, dict[str, Any]],
    friendly_player_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Keep damage taken events that target actual players in the selected fight."""
    allowed_targets = set(friendly_player_ids or [])
    filtered: list[dict[str, Any]] = []

    for event in events:
        target_id = event.get("targetID")
        if target_id is None:
            continue

        source_id = event.get("sourceID")
        source = actors.get(int(source_id)) if source_id is not None else None
        if source and (
            source.get("type") == "Player"
            or source.get("petOwner") is not None
        ):
            continue

        target = actors.get(int(target_id))
        if not target or target.get("type") != "Player":
            continue
        if allowed_targets and int(target_id) not in allowed_targets:
            continue

        filtered.append(event)

    return filtered
