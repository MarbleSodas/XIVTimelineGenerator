"""Deterministic ability matching helpers."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from .models import AbilityMatch, ExtractedAction

TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_name(value: str) -> str:
    tokens = TOKEN_PATTERN.findall(value.lower())
    return " ".join(tokens)


def tokenize(value: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(value.lower()))


def match_actions_for_ability(
    ability_name: str,
    actions: list[ExtractedAction],
    *,
    minimum_score: float = 0.55,
) -> list[AbilityMatch]:
    normalized_ability = normalize_name(ability_name)
    ability_tokens = tokenize(ability_name)
    matches: list[AbilityMatch] = []

    for action in actions:
        normalized_action = normalize_name(action.action_name)
        if not normalized_action:
            continue

        score = 0.0
        strategy = "none"
        if normalized_action == normalized_ability:
            score = 1.0
            strategy = "exact"
        elif normalized_action in normalized_ability or normalized_ability in normalized_action:
            score = 0.9
            strategy = "substring"
        else:
            token_overlap = len(ability_tokens & tokenize(action.action_name))
            token_count = max(len(ability_tokens), len(tokenize(action.action_name)), 1)
            overlap_score = token_overlap / token_count
            ratio_score = SequenceMatcher(None, normalized_ability, normalized_action).ratio()
            score = max(ratio_score, overlap_score)
            strategy = "fuzzy" if score >= minimum_score else "none"

        if score >= minimum_score:
            matches.append(
                AbilityMatch(
                    ability_name=ability_name,
                    action=action,
                    score=round(score, 4),
                    strategy=strategy,
                )
            )

    matches.sort(key=lambda item: (-item.score, item.action.site, item.action.action_name.lower()))
    return matches
