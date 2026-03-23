from pathlib import Path

from agents.encounter_research.service import EncounterResearchService


class FakeSearchClient:
    def __init__(self):
        self.search_calls = []
        self.fetch_calls = []

    def search(self, query, limit=5):
        self.search_calls.append((query, limit))
        if "icy-veins.com" in query:
            return [
                type(
                    "Result",
                    (),
                    {
                        "title": "Icy Veins Guide",
                        "url": "https://www.icy-veins.com/ffxiv/m11s-guide",
                        "description": "",
                        "source": "Icy Veins",
                        "engine": "duckduckgo",
                        "to_dict": lambda self: {
                            "title": self.title,
                            "url": self.url,
                            "description": self.description,
                            "source": self.source,
                            "engine": self.engine,
                        },
                    },
                )()
            ]
        return [
            type(
                "Result",
                (),
                {
                    "title": "Hardcore Gamer Guide",
                    "url": "https://www.hardcoregamer.com/m11s",
                    "description": "",
                    "source": "Hardcore Gamer",
                    "engine": "bing",
                    "to_dict": lambda self: {
                        "title": self.title,
                        "url": self.url,
                        "description": self.description,
                        "source": self.source,
                        "engine": self.engine,
                    },
                },
            )()
        ]

    def fetch_web_content(self, url, max_chars=30000):
        self.fetch_calls.append((url, max_chars))
        if "icy-veins" in url:
            return type(
                "Document",
                (),
                {
                    "site": "icy-veins",
                    "url": url,
                    "final_url": url,
                    "title": "Icy Veins Guide",
                    "content": "Crown of Arcadia is a raidwide blast.",
                    "content_type": "text/html",
                    "truncated": False,
                    "to_dict": lambda self: {
                        "site": self.site,
                        "url": self.url,
                        "final_url": self.final_url,
                        "title": self.title,
                        "content": self.content,
                        "content_type": self.content_type,
                        "truncated": self.truncated,
                    },
                },
            )()
        return type(
            "Document",
            (),
            {
                "site": "hardcore-gamer",
                "url": url,
                "final_url": url,
                "title": "Hardcore Gamer Guide",
                "content": "Raw Steel is shared between both tanks.",
                "content_type": "text/html",
                "truncated": False,
                "to_dict": lambda self: {
                    "site": self.site,
                    "url": self.url,
                    "final_url": self.final_url,
                    "title": self.title,
                    "content": self.content,
                    "content_type": self.content_type,
                    "truncated": self.truncated,
                },
            },
        )()


class FakeMiniMaxClient:
    def chat_json(self, system_prompt, user_prompt, **kwargs):
        if "Icy Veins Guide" in user_prompt:
            return {
                "actions": [
                    {
                        "phase": "Phase 1",
                        "action_name": "Crown of Arcadia",
                        "description": "Raidwide blast that hits the full party.",
                        "classification": "raidwide",
                        "is_dot": False,
                        "is_multi_hit": False,
                        "damage_link_likelihood": 0.95,
                        "evidence_quote": "raidwide blast",
                    }
                ]
            }
        if "Hardcore Gamer Guide" in user_prompt:
            return {
                "actions": [
                    {
                        "phase": "Phase 1",
                        "action_name": "Raw Steel",
                        "description": "Dual tankbuster on both tanks.",
                        "classification": "dual_tankbuster",
                        "is_dot": False,
                        "is_multi_hit": True,
                        "damage_link_likelihood": 0.9,
                        "evidence_quote": "shared between both tanks",
                    }
                ]
            }
        return {
            "status": "disputed",
            "confidence": 0.5,
            "description": None,
            "classification": None,
            "rationale": "conflict",
        }


def test_service_enriches_generated_timeline_events(tmp_path):
    service = EncounterResearchService(
        search_client=FakeSearchClient(),
        llm_client=FakeMiniMaxClient(),
        cache_dir=tmp_path,
    )
    encounter = {
        "code": "M11S",
        "full_name": "AAC Heavyweight M3 (Savage)",
        "boss_name": "The Tyrant",
    }
    timelines = [
        {
            "encounter_code": "M11S",
            "fight_index": 0,
            "branch_index": 0,
            "events": [
                {
                    "timestamp": "00:05.000",
                    "timestamp_ms": 5000,
                    "ability_name": "Crown of Arcadia",
                    "classification": "raidwide",
                    "is_dot": False,
                    "is_multi_hit": False,
                },
                {
                    "timestamp": "00:08.000",
                    "timestamp_ms": 8000,
                    "ability_name": "Raw Steel",
                    "classification": "dual_tankbuster",
                    "is_dot": False,
                    "is_multi_hit": True,
                },
            ],
        }
    ]

    enriched = service.enrich_generated_timelines(encounter, timelines)

    first_event = enriched[0]["events"][0]
    second_event = enriched[0]["events"][1]
    assert first_event["research_status"] == "matched"
    assert first_event["research_description"] == "Raidwide blast that hits the full party."
    assert first_event["research_classification"] == "raidwide"
    assert first_event["research_is_dot"] is False
    assert first_event["research_is_multi_hit"] is False
    assert second_event["research_classification"] == "dual_tankbuster"
    assert second_event["research_is_dot"] is False
    assert second_event["research_is_multi_hit"] is True
    assert len(second_event["research_sources"]) == 1


def test_service_marks_no_source_when_live_search_is_skipped_without_cache(tmp_path):
    service = EncounterResearchService(
        search_client=FakeSearchClient(),
        llm_client=FakeMiniMaxClient(),
        cache_dir=tmp_path / "empty",
        skip_live_search=True,
    )
    encounter = {
        "code": "M11S",
        "full_name": "AAC Heavyweight M3 (Savage)",
        "boss_name": "The Tyrant",
    }
    timelines = [
        {
            "encounter_code": "M11S",
            "fight_index": 0,
            "branch_index": 0,
            "events": [
                {"timestamp": "00:05.000", "timestamp_ms": 5000, "ability_name": "Crown of Arcadia"}
            ],
        }
    ]

    enriched = service.enrich_generated_timelines(encounter, timelines)

    assert enriched[0]["events"][0]["research_status"] == "no_source"


def test_service_reuses_cached_actions_when_available(tmp_path):
    service = EncounterResearchService(
        search_client=FakeSearchClient(),
        llm_client=FakeMiniMaxClient(),
        cache_dir=tmp_path,
    )
    encounter = {
        "code": "M11S",
        "full_name": "AAC Heavyweight M3 (Savage)",
        "boss_name": "The Tyrant",
    }
    timelines = [
        {
            "encounter_code": "M11S",
            "fight_index": 0,
            "branch_index": 0,
            "events": [
                {"timestamp": "00:05.000", "timestamp_ms": 5000, "ability_name": "Crown of Arcadia"}
            ],
        }
    ]

    service.enrich_generated_timelines(encounter, timelines)

    offline_service = EncounterResearchService(
        search_client=FakeSearchClient(),
        llm_client=FakeMiniMaxClient(),
        cache_dir=tmp_path,
        skip_live_search=True,
    )
    enriched = offline_service.enrich_generated_timelines(encounter, timelines)

    assert enriched[0]["events"][0]["research_status"] == "matched"
