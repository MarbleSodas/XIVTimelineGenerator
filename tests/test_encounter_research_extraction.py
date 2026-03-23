from pathlib import Path

from agents.encounter_research.extractors import GuideExtractor, clean_document_content
from agents.encounter_research.models import SourceDocument


class FakeMiniMaxClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def chat_json(self, system_prompt, user_prompt, **kwargs):
        self.calls.append((system_prompt, user_prompt, kwargs))
        return self.payload


def _fixture_text(name: str) -> str:
    path = Path("tests/fixtures/encounter_research") / name
    return path.read_text(encoding="utf-8")


def test_clean_document_content_collapses_blank_lines():
    raw = "\n\n Crown of Arcadia \n\n is a raidwide. \n\n"

    cleaned = clean_document_content(raw)

    assert cleaned == "Crown of Arcadia\nis a raidwide."


def test_guide_extractor_maps_llm_payload_to_extracted_actions():
    client = FakeMiniMaxClient(
        {
            "actions": [
                {
                    "phase": "Phase 1",
                    "action_name": "Crown of Arcadia",
                    "description": "Raidwide party damage.",
                    "classification": "raidwide",
                    "is_dot": False,
                    "is_multi_hit": False,
                    "damage_link_likelihood": 0.95,
                    "evidence_quote": "Crown of Arcadia is a raidwide blast",
                },
                {
                    "phase": "Phase 1",
                    "action_name": "Flavor text",
                    "description": "Ignore this.",
                    "classification": None,
                    "is_dot": False,
                    "is_multi_hit": False,
                    "damage_link_likelihood": 0.1,
                    "evidence_quote": "General strategy",
                },
            ]
        }
    )
    extractor = GuideExtractor(client)
    document = SourceDocument(
        site="icy-veins",
        url="https://www.icy-veins.com/ffxiv/m11s-guide",
        title="Icy Veins M11S",
        content=_fixture_text("icy_veins_m11s.html"),
    )

    actions = extractor.extract_actions(document)

    assert len(actions) == 1
    assert actions[0].site == "icy-veins"
    assert actions[0].action_name == "Crown of Arcadia"
    assert actions[0].classification == "raidwide"
    assert actions[0].is_dot is False
    assert actions[0].is_multi_hit is False
    assert "Icy Veins M11S" in client.calls[0][1]


def test_guide_extractor_handles_hardcore_gamer_fixture():
    client = FakeMiniMaxClient(
        {
            "actions": [
                {
                    "phase": None,
                    "action_name": "Raw Steel",
                    "description": "Dual tankbuster.",
                    "classification": "dual_tankbuster",
                    "is_dot": False,
                    "is_multi_hit": True,
                    "damage_link_likelihood": 0.9,
                    "evidence_quote": "Raw Steel is shared between both tanks",
                }
            ]
        }
    )
    extractor = GuideExtractor(client)
    document = SourceDocument(
        site="hardcore-gamer",
        url="https://www.hardcoregamer.com/m11s",
        title="Hardcore Gamer M11S",
        content=_fixture_text("hardcore_gamer_m11s.html"),
    )

    actions = extractor.extract_actions(document)

    assert len(actions) == 1
    assert actions[0].phase is None
    assert actions[0].classification == "dual_tankbuster"
    assert actions[0].is_dot is False
    assert actions[0].is_multi_hit is True
