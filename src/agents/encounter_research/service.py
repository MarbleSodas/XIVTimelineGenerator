"""Encounter research orchestration."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .cache import ResearchCache
from .discovery import discover_guide_documents
from .extractors import GuideExtractor
from .matcher import match_actions_for_ability
from .models import ExtractedAction, ResearchAnnotation, SourceDocument
from .reconciler import reconcile_match_results


class EncounterResearchService:
    def __init__(
        self,
        *,
        search_client: Any,
        llm_client: Any,
        cache_dir: Path,
        skip_live_search: bool = False,
        search_limit: int = 3,
    ):
        self.search_client = search_client
        self.llm_client = llm_client
        self.cache = ResearchCache(cache_dir)
        self.skip_live_search = skip_live_search
        self.search_limit = search_limit

    def enrich_generated_timelines(
        self,
        encounter_config: dict[str, Any],
        generated_timelines: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        ability_catalog = self._load_or_build_action_catalog(encounter_config)
        research_available = bool(ability_catalog)
        annotations = self._build_annotations(generated_timelines, ability_catalog, research_available)

        enriched_timelines: list[dict[str, Any]] = []
        for timeline in generated_timelines:
            timeline_copy = deepcopy(timeline)
            timeline_copy["events"] = [
                self._annotate_event(event, annotations, research_available)
                for event in timeline.get("events") or []
            ]
            enriched_timelines.append(timeline_copy)
        return enriched_timelines

    def _load_or_build_action_catalog(
        self,
        encounter_config: dict[str, Any],
    ) -> list[ExtractedAction]:
        cache_key = str(encounter_config.get("code") or "unknown")
        cached = self.cache.load_json("actions", cache_key)
        if isinstance(cached, list):
            return [ExtractedAction(**item) for item in cached]

        if self.skip_live_search:
            return []

        search_cache_key = f"{cache_key}-search"
        searches = self.cache.load_json("searches", search_cache_key)
        documents_payload = self.cache.load_json("documents", cache_key)

        if searches is None or documents_payload is None:
            search_results, documents = discover_guide_documents(
                encounter_config,
                self.search_client,
                limit_per_query=self.search_limit,
            )
            self.cache.save_json(
                "searches",
                search_cache_key,
                [result.to_dict() for result in search_results],
            )
            self.cache.save_json(
                "documents",
                cache_key,
                [document.to_dict() for document in documents],
            )
        else:
            documents = [SourceDocument(**item) for item in documents_payload]

        extractor = GuideExtractor(self.llm_client)
        actions: list[ExtractedAction] = []
        for document in documents:
            actions.extend(extractor.extract_actions(document))

        self.cache.save_json("actions", cache_key, [action.to_dict() for action in actions])
        return actions

    def _build_annotations(
        self,
        generated_timelines: list[dict[str, Any]],
        actions: list[ExtractedAction],
        research_available: bool,
    ) -> dict[str, ResearchAnnotation]:
        annotations: dict[str, ResearchAnnotation] = {}
        for ability_name, heuristic_label in self._collect_ability_hints(generated_timelines).items():
            matches = match_actions_for_ability(ability_name, actions)
            if not research_available:
                annotations[ability_name] = ResearchAnnotation(
                    status="no_source",
                    confidence=0.0,
                    description=None,
                    classification=None,
                    is_dot=None,
                    is_multi_hit=None,
                    sources=[],
                    discrepancy=None,
                )
                continue
            annotations[ability_name] = reconcile_match_results(
                ability_name,
                matches,
                heuristic_label=heuristic_label,
                llm_client=self.llm_client if len(matches) > 1 else None,
            )
        return annotations

    @staticmethod
    def _collect_ability_hints(
        generated_timelines: list[dict[str, Any]],
    ) -> dict[str, str | None]:
        hints: dict[str, str | None] = {}
        for timeline in generated_timelines:
            for event in timeline.get("events") or []:
                heuristic_label = _build_heuristic_label(
                    classification=event.get("classification"),
                    is_dot=event.get("is_dot"),
                    is_multi_hit=event.get("is_multi_hit"),
                )
                if event.get("ability_name"):
                    hints.setdefault(str(event["ability_name"]), _coerce_single_value(heuristic_label))
                for index, ability_name in enumerate(event.get("ability_names") or []):
                    hints.setdefault(str(ability_name), _indexed_value(heuristic_label, index))
        return hints

    def _annotate_event(
        self,
        event: dict[str, Any],
        annotations: dict[str, ResearchAnnotation],
        research_available: bool,
    ) -> dict[str, Any]:
        annotated = deepcopy(event)
        if annotated.get("ability_name"):
            annotation = annotations.get(str(annotated["ability_name"])) or self._fallback_annotation(research_available)
            annotated.update(annotation.to_dict())
            return annotated

        ability_names = [str(name) for name in annotated.get("ability_names") or []]
        if not ability_names:
            annotated.update(self._fallback_annotation(research_available).to_dict())
            return annotated

        event_annotations = [
            annotations.get(name) or self._fallback_annotation(research_available)
            for name in ability_names
        ]
        annotated["research_status"] = [
            annotation.status for annotation in event_annotations
        ]
        annotated["research_confidence"] = [
            round(annotation.confidence, 4) for annotation in event_annotations
        ]
        annotated["research_description"] = [
            annotation.description for annotation in event_annotations
        ]
        annotated["research_classification"] = [
            annotation.classification for annotation in event_annotations
        ]
        annotated["research_is_dot"] = [
            annotation.is_dot for annotation in event_annotations
        ]
        annotated["research_is_multi_hit"] = [
            annotation.is_multi_hit for annotation in event_annotations
        ]
        annotated["research_discrepancy"] = [
            annotation.discrepancy for annotation in event_annotations
        ]
        seen_sources: set[tuple[str, str]] = set()
        merged_sources: list[dict[str, Any]] = []
        for annotation in event_annotations:
            for source in annotation.sources:
                key = (source.site, source.url)
                if key in seen_sources:
                    continue
                seen_sources.add(key)
                merged_sources.append(source.to_dict())
        annotated["research_sources"] = merged_sources
        return annotated

    @staticmethod
    def _fallback_annotation(research_available: bool) -> ResearchAnnotation:
        return ResearchAnnotation(
            status="unmatched" if research_available else "no_source",
            confidence=0.0,
            description=None,
            classification=None,
            is_dot=None,
            is_multi_hit=None,
            sources=[],
            discrepancy=None,
        )


def _coerce_single_value(value: Any) -> str | None:
    if isinstance(value, list):
        return str(value[0]) if value else None
    if value is None:
        return None
    return str(value)


def _indexed_value(value: Any, index: int) -> str | None:
    if isinstance(value, list):
        if index < len(value):
            return str(value[index]) if value[index] is not None else None
        return None
    if value is None:
        return None
    return str(value)


def _build_heuristic_label(
    *,
    classification: Any,
    is_dot: Any,
    is_multi_hit: Any,
) -> str | list[str] | None:
    if isinstance(classification, list):
        return [
            _decorate_heuristic_value(item, _list_bool_value(is_dot, index), _list_bool_value(is_multi_hit, index))
            for index, item in enumerate(classification)
        ]
    return _decorate_heuristic_value(classification, is_dot, is_multi_hit)


def _decorate_heuristic_value(
    classification: Any,
    is_dot: Any,
    is_multi_hit: Any,
) -> str | None:
    if classification is None:
        return None
    label = str(classification)
    if bool(is_dot):
        label = f"{label}:dot"
    if bool(is_multi_hit):
        label = f"{label}:multi_hit"
    return label


def _list_bool_value(value: Any, index: int) -> Any:
    if not isinstance(value, list):
        return value
    if index >= len(value):
        return None
    return value[index]
