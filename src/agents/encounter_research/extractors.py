"""LLM-assisted source extraction helpers."""

from __future__ import annotations

from .minimax_client import MiniMaxClient
from .models import ExtractedAction, SourceDocument

EXTRACTION_SYSTEM_PROMPT = """
You extract Final Fantasy XIV boss actions from raid guide text.
Return JSON only with this shape:
{
  "actions": [
    {
      "phase": "string or null",
      "action_name": "string",
      "description": "short string",
      "classification": "raidwide|tankbuster|dual_tankbuster|small_party|null",
      "is_dot": true,
      "is_multi_hit": false,
      "damage_link_likelihood": 0.0,
      "evidence_quote": "short excerpt from the document"
    }
  ]
}
Only include boss actions that look linkable to unavoidable damage timeline events.
Exclude dodgeable mechanics such as spreads, stacks, line/cone/circle/donut AOEs,
knockbacks, proximity mechanics, movement failures, and generic strategy advice.
Keep damage_link_likelihood between 0 and 1.
""".strip()


def clean_document_content(content: str, max_chars: int = 12000) -> str:
    lines = [line.strip() for line in content.splitlines()]
    non_empty = [line for line in lines if line]
    cleaned = "\n".join(non_empty)
    return cleaned[:max_chars]


class GuideExtractor:
    def __init__(self, llm_client: MiniMaxClient):
        self.llm_client = llm_client

    def extract_actions(self, document: SourceDocument) -> list[ExtractedAction]:
        prompt = self._build_prompt(document)
        payload = self.llm_client.chat_json(
            EXTRACTION_SYSTEM_PROMPT,
            prompt,
        )
        actions = payload.get("actions") or []
        extracted: list[ExtractedAction] = []
        for item in actions:
            action_name = str(item.get("action_name") or "").strip()
            description = str(item.get("description") or "").strip()
            if not action_name or not description:
                continue
            likelihood = float(item.get("damage_link_likelihood") or 0.0)
            if likelihood < 0.35:
                continue
            extracted.append(
                ExtractedAction(
                    site=document.site,
                    url=document.final_url or document.url,
                    title=document.title,
                    phase=_optional_string(item.get("phase")),
                    action_name=action_name,
                    description=description,
                    classification=_optional_string(item.get("classification")),
                    is_dot=_optional_bool(item.get("is_dot")),
                    is_multi_hit=_optional_bool(item.get("is_multi_hit")),
                    damage_link_likelihood=max(0.0, min(1.0, likelihood)),
                    evidence_quote=str(item.get("evidence_quote") or "").strip(),
                )
            )
        return extracted

    @staticmethod
    def _build_prompt(document: SourceDocument) -> str:
        cleaned = clean_document_content(document.content)
        return (
            f"Site: {document.site}\n"
            f"Title: {document.title}\n"
            f"URL: {document.final_url or document.url}\n"
            f"Document:\n{cleaned}"
        )


def _optional_string(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _optional_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes"}
