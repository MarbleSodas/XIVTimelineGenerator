"""Research reconciliation helpers."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .minimax_client import MiniMaxClient
from .models import AbilityMatch, ResearchAnnotation, ResearchSourceRef

ADJUDICATION_SYSTEM_PROMPT = """
You adjudicate conflicting Final Fantasy XIV raid-mechanic guide evidence.
Return JSON only with this shape:
{
  "status": "matched|disputed|unmatched|no_source",
  "confidence": 0.0,
  "description": "string or null",
  "classification": "string or null",
  "is_dot": "boolean or null",
  "is_multi_hit": "boolean or null",
  "rationale": "short string"
}
Prefer conservative outputs. If evidence is weak or contradictory, return disputed.
""".strip()

HEURISTIC_CLASSIFICATION_MAP = {
    "tankbuster": "tankbuster",
    "dual_tankbuster": "dual_tankbuster",
    "raidwide": "raidwide",
    "small_party": "small_party",
}


def reconcile_match_results(
    ability_name: str,
    matches: list[AbilityMatch],
    *,
    heuristic_label: str | None = None,
    llm_client: MiniMaxClient | None = None,
) -> ResearchAnnotation:
    if not matches:
        return ResearchAnnotation(
            status="unmatched",
            confidence=0.0,
            description=None,
            classification=_heuristic_to_research_classification(heuristic_label),
            is_dot=_heuristic_is_dot(heuristic_label),
            is_multi_hit=_heuristic_is_multi_hit(heuristic_label),
            sources=[],
            discrepancy=None,
        )

    top_matches = _top_band(matches)
    descriptions = Counter(match.action.description for match in top_matches if match.action.description)
    classifications = Counter(
        match.action.classification for match in top_matches if match.action.classification
    )

    unique_sources = _sources_for_matches(top_matches)
    top_score = top_matches[0].score
    heuristic_classification = _heuristic_to_research_classification(heuristic_label)
    heuristic_is_dot = _heuristic_is_dot(heuristic_label)
    heuristic_is_multi_hit = _heuristic_is_multi_hit(heuristic_label)

    if len(top_matches) == 1 and top_score >= 0.9:
        selected = top_matches[0]
        classification = selected.action.classification or heuristic_classification
        return ResearchAnnotation(
            status="matched",
            confidence=top_score,
            description=selected.action.description,
            classification=classification,
            is_dot=selected.action.is_dot,
            is_multi_hit=selected.action.is_multi_hit,
            sources=unique_sources,
            discrepancy=None,
        )

    if (
        len(descriptions) == 1
        and len(classifications or {None: 1}) <= 1
        and top_score >= 0.75
    ):
        sole_match = top_matches[0]
        classification = sole_match.action.classification or heuristic_classification
        return ResearchAnnotation(
            status="matched",
            confidence=min(0.95, top_score),
            description=sole_match.action.description,
            classification=classification,
            is_dot=sole_match.action.is_dot,
            is_multi_hit=sole_match.action.is_multi_hit,
            sources=unique_sources,
            discrepancy=None,
        )

    if llm_client is not None:
        annotation = _adjudicate_with_llm(
            ability_name=ability_name,
            matches=top_matches,
            heuristic_classification=heuristic_classification,
            heuristic_is_dot=heuristic_is_dot,
            heuristic_is_multi_hit=heuristic_is_multi_hit,
            llm_client=llm_client,
        )
        if annotation is not None:
            return annotation

    discrepancy = {
        "reason": "conflicting_guide_evidence",
        "candidates": [
            {
                "site": match.action.site,
                "action_name": match.action.action_name,
                "description": match.action.description,
                "classification": match.action.classification,
                "score": match.score,
            }
            for match in top_matches
        ],
    }
    return ResearchAnnotation(
        status="disputed",
        confidence=min(0.7, top_score),
        description=top_matches[0].action.description,
        classification=top_matches[0].action.classification or heuristic_classification,
        is_dot=top_matches[0].action.is_dot,
        is_multi_hit=top_matches[0].action.is_multi_hit,
        sources=unique_sources,
        discrepancy=discrepancy,
    )


def _top_band(matches: list[AbilityMatch]) -> list[AbilityMatch]:
    top_score = matches[0].score
    threshold = max(0.0, top_score - 0.08)
    return [match for match in matches if match.score >= threshold]


def _sources_for_matches(matches: list[AbilityMatch]) -> list[ResearchSourceRef]:
    seen: set[tuple[str, str]] = set()
    sources: list[ResearchSourceRef] = []
    for match in matches:
        key = (match.action.site, match.action.url)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            ResearchSourceRef(
                site=match.action.site,
                url=match.action.url,
                title=match.action.title,
            )
        )
    return sources


def _heuristic_to_research_classification(value: str | None) -> str | None:
    base_value, _ = _split_heuristic_label(value)
    if base_value is None:
        return None
    return HEURISTIC_CLASSIFICATION_MAP.get(base_value, base_value)


def _heuristic_is_dot(value: str | None) -> bool | None:
    if value is None:
        return None
    _, modifiers = _split_heuristic_label(value)
    return "dot" in modifiers


def _heuristic_is_multi_hit(value: str | None) -> bool | None:
    if value is None:
        return None
    _, modifiers = _split_heuristic_label(value)
    return "multi_hit" in modifiers


def _adjudicate_with_llm(
    *,
    ability_name: str,
    matches: list[AbilityMatch],
    heuristic_classification: str | None,
    heuristic_is_dot: bool | None,
    heuristic_is_multi_hit: bool | None,
    llm_client: MiniMaxClient,
) -> ResearchAnnotation | None:
    prompt = {
        "ability_name": ability_name,
        "heuristic_classification": heuristic_classification,
        "heuristic_is_dot": heuristic_is_dot,
        "heuristic_is_multi_hit": heuristic_is_multi_hit,
        "candidates": [
            {
                "site": match.action.site,
                "action_name": match.action.action_name,
                "description": match.action.description,
                "classification": match.action.classification,
                "is_dot": match.action.is_dot,
                "is_multi_hit": match.action.is_multi_hit,
                "evidence_quote": match.action.evidence_quote,
                "score": match.score,
                "strategy": match.strategy,
            }
            for match in matches
        ],
    }
    payload = llm_client.chat_json(
        ADJUDICATION_SYSTEM_PROMPT,
        str(prompt),
    )
    status = str(payload.get("status") or "disputed")
    confidence = max(0.0, min(1.0, float(payload.get("confidence") or 0.0)))
    description = _optional_string(payload.get("description"))
    classification = _optional_string(payload.get("classification")) or heuristic_classification
    is_dot = _optional_bool(payload.get("is_dot"), heuristic_is_dot)
    is_multi_hit = _optional_bool(payload.get("is_multi_hit"), heuristic_is_multi_hit)
    rationale = _optional_string(payload.get("rationale"))
    if status not in {"matched", "disputed", "unmatched", "no_source"}:
        status = "disputed"
    if status == "matched" and confidence < 0.55:
        status = "disputed"
    return ResearchAnnotation(
        status=status,
        confidence=confidence,
        description=description,
        classification=classification,
        is_dot=is_dot,
        is_multi_hit=is_multi_hit,
        sources=_sources_for_matches(matches),
        discrepancy={"reason": "llm_adjudication", "rationale": rationale} if rationale else None,
    )


def _optional_string(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _optional_bool(value: Any, default: bool | None = None) -> bool | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no"}:
        return False
    return default


def _split_heuristic_label(value: str | None) -> tuple[str | None, set[str]]:
    if value is None:
        return None, set()
    parts = [part.strip() for part in str(value).split(":") if part.strip()]
    if not parts:
        return None, set()
    return parts[0], set(parts[1:])
