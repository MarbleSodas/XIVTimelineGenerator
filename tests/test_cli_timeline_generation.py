import argparse
import json


class FakeFFLogsGraphQLClient:
    def resolve_encounter_id(self, **kwargs):
        return 1234

    def fetch_reports(self, **kwargs):
        return [{"code": "R1", "fights": [{"id": 1}]}]

    def fetch_report_details(self, report_code, encounter_id):
        return {
            "code": report_code,
            "title": "Report One",
            "startTime": 0,
            "endTime": 60_000,
            "fights": [
                {
                    "id": 1,
                    "name": "The Tyrant",
                    "startTime": 0,
                    "endTime": 60_000,
                    "friendlyPlayers": [1, 2, 3, 4, 5, 6, 7, 8],
                }
            ],
            "actors": [],
            "abilities": [],
        }

    def fetch_events(self, report_code, fight_id, start_time, end_time):
        return []


def build_args(tmp_path, **overrides):
    defaults = {
        "encounter": "M11S",
        "limit": 1,
        "output_dir": tmp_path,
        "postprocessed_dir": None,
        "postprocessed_aligned_dir": None,
        "generated_timelines_dir": None,
        "research_mechanics": False,
        "open_websearch_command": "npx",
        "open_websearch_package": "open-websearch@latest",
        "research_cache_dir": tmp_path / ".research_cache",
        "skip_live_search": False,
        "search_engines": "duckduckgo,bing,exa",
        "research_llm_model": "MiniMax-M2.7",
        "timeline_llm_model": "MiniMax-M2.7",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def make_postprocessed_report():
    return {
        "encounter": {"code": "M11S"},
        "report": {"code": "R1"},
        "fights": [
            {
                "fight_index": 0,
                "fight_id": 1,
                "fight_name": "The Tyrant",
                "party_size": 8,
                "damage_events": [
                    {
                        "timestamp": "00:10.000",
                        "timestamp_ms": 10_000,
                        "ability_name": "Crown of Arcadia",
                        "unmitigated_damage": 200_000,
                        "ability_type": "physical",
                        "hit_type": "landed",
                        "target_id": 101,
                        "target_subtype": "Warrior",
                        "target_name": "Tank One",
                        "is_dot": False,
                        "multiplier": 1.0,
                    }
                ],
            }
        ],
    }


def make_aligned_report():
    return make_postprocessed_report()


def test_cli_uses_atomic_agent_and_writes_encounter_timeline(tmp_path, monkeypatch):
    from fflogs_damage_timeline import cli

    aligned_report = make_aligned_report()
    process_calls = []

    monkeypatch.setattr(cli, "FFLogsGraphQLClient", lambda: FakeFFLogsGraphQLClient())
    monkeypatch.setattr(
        cli,
        "load_encounter_config",
        lambda encounter_code: {
            "code": "M11S",
            "full_name": "AAC Heavyweight M3 (Savage)",
            "boss_name": "The Tyrant",
            "zone_id": 73,
            "encounter_id": 1234,
            "expansion": "dawntrail",
            "category": "savage",
        },
    )
    monkeypatch.setattr(cli, "normalize_fight_timeline", lambda **kwargs: {"fight_id": 1, "events": []})
    monkeypatch.setattr(cli, "build_postprocessed_report", lambda report_timeline: make_postprocessed_report())
    monkeypatch.setattr(cli, "build_aligned_postprocessed_reports", lambda reports: [aligned_report])
    monkeypatch.setattr(cli, "build_timeline_llm_client", lambda args: object())

    def fake_process_reports(aligned_reports, encounter_config, llm_client):
        process_calls.append((aligned_reports, encounter_config, llm_client))
        return {
            "encounter_code": "M11S",
            "report_codes": ["R1"],
            "report_count": 1,
            "aligned_fight_count": 1,
            "source_fight_indexes": [0],
            "events": [
                {
                    "timestamp": "00:10.000",
                    "timestamp_ms": 10_000,
                    "event_kind": "stable",
                    "ability_name": "Crown of Arcadia",
                    "classification": "raidwide",
                    "is_dot": False,
                    "is_multi_hit": False,
                    "unmitigated_damage": 200_000,
                    "ability_type": "physical",
                    "support_report_count": 1,
                    "support_fight_count": 1,
                    "support_fight_indexes": [0],
                }
            ],
        }

    monkeypatch.setattr(cli, "process_reports", fake_process_reports)

    result = cli.run(build_args(tmp_path))

    assert result == 0
    assert len(process_calls) == 1
    assert process_calls[0][0] == [aligned_report]
    assert process_calls[0][1]["code"] == "M11S"

    encounter_path = tmp_path / "M11S" / "generated" / "encounter.timeline.json"
    assert encounter_path.exists()
    assert list((tmp_path / "M11S" / "generated").glob("fight-*-branch-*.timeline.json")) == []
    assert (tmp_path / "M11S" / "reports" / "R1.json").exists()
    assert (tmp_path / "M11S" / "postprocessed" / "R1.postprocessed.json").exists()
    assert (tmp_path / "M11S" / "aligned" / "R1.aligned.json").exists()

    with encounter_path.open() as file_handle:
        payload = json.load(file_handle)
    assert payload["events"][0]["ability_name"] == "Crown of Arcadia"


def test_cli_returns_nonzero_when_atomic_agent_generation_fails(tmp_path, monkeypatch):
    from fflogs_damage_timeline import cli

    monkeypatch.setattr(cli, "FFLogsGraphQLClient", lambda: FakeFFLogsGraphQLClient())
    monkeypatch.setattr(
        cli,
        "load_encounter_config",
        lambda encounter_code: {
            "code": "M11S",
            "full_name": "AAC Heavyweight M3 (Savage)",
            "boss_name": "The Tyrant",
            "zone_id": 73,
            "encounter_id": 1234,
            "expansion": "dawntrail",
            "category": "savage",
        },
    )
    monkeypatch.setattr(cli, "normalize_fight_timeline", lambda **kwargs: {"fight_id": 1, "events": []})
    monkeypatch.setattr(cli, "build_postprocessed_report", lambda report_timeline: make_postprocessed_report())
    monkeypatch.setattr(cli, "build_aligned_postprocessed_reports", lambda reports: [make_aligned_report()])
    monkeypatch.setattr(cli, "build_timeline_llm_client", lambda args: object())
    monkeypatch.setattr(
        cli,
        "process_reports",
        lambda aligned_reports, encounter_config, llm_client: (_ for _ in ()).throw(
            RuntimeError("OPENAI_API_KEY is required for MiniMax requests")
        ),
    )

    result = cli.run(build_args(tmp_path))

    assert result == 1
    assert (tmp_path / "M11S" / "aligned" / "R1.aligned.json").exists()
    assert not (tmp_path / "M11S" / "generated" / "encounter.timeline.json").exists()
