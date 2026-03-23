"""Typed models for encounter research."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    description: str = ""
    source: str = ""
    engine: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceDocument:
    site: str
    url: str
    title: str
    content: str
    final_url: str | None = None
    content_type: str | None = None
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchSourceRef:
    site: str
    url: str
    title: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExtractedAction:
    site: str
    url: str
    title: str
    phase: str | None
    action_name: str
    description: str
    classification: str | None
    is_dot: bool
    is_multi_hit: bool
    damage_link_likelihood: float
    evidence_quote: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AbilityMatch:
    ability_name: str
    action: ExtractedAction
    score: float
    strategy: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["action"] = self.action.to_dict()
        return payload


@dataclass(frozen=True)
class ResearchAnnotation:
    status: str
    confidence: float
    description: str | None
    classification: str | None
    is_dot: bool | None = None
    is_multi_hit: bool | None = None
    sources: list[ResearchSourceRef] = field(default_factory=list)
    discrepancy: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "research_status": self.status,
            "research_confidence": round(float(self.confidence), 4),
            "research_description": self.description,
            "research_classification": self.classification,
            "research_is_dot": self.is_dot,
            "research_is_multi_hit": self.is_multi_hit,
            "research_sources": [source.to_dict() for source in self.sources],
            "research_discrepancy": self.discrepancy,
        }
