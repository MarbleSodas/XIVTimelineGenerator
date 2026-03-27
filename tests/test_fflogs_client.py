from fflogs_damage_timeline.graphql_client import (
    FFLogsGraphQLClient,
    FETCH_EVENTS_QUERY,
    FETCH_PLAYER_DETAILS_QUERY,
    FETCH_REPORT_DETAILS_QUERY,
    FETCH_REPORTS_PAGE_QUERY,
)


def test_resolve_encounter_id_matches_boss_name():
    client = FFLogsGraphQLClient("id", "secret")
    client._post_graphql = lambda query, variables: {
        "worldData": {
            "zone": {
                "id": 73,
                "name": "AAC Heavyweight",
                "encounters": [
                    {"id": 101, "name": "Vamp Fatale"},
                    {"id": 103, "name": "The Tyrant"},
                ],
            }
        }
    }

    encounter_id = client.resolve_encounter_id(zone_id=73, boss_name="The Tyrant")
    assert encounter_id == 103


def test_fetch_reports_pages_until_limit_and_keeps_matching_reports():
    client = FFLogsGraphQLClient("id", "secret")
    responses = iter(
        [
            {
                "reportData": {
                    "reports": {
                        "current_page": 1,
                        "has_more_pages": True,
                        "data": [
                            {"code": "A", "title": "No Kill", "fights": []},
                            {
                                "code": "B",
                                "title": "Match 1",
                                "fights": [{"id": 1, "kill": True}],
                            },
                        ],
                    }
                }
            },
            {
                "reportData": {
                    "reports": {
                        "current_page": 2,
                        "has_more_pages": False,
                        "data": [
                            {
                                "code": "C",
                                "title": "Match 2",
                                "fights": [{"id": 2, "kill": True}],
                            }
                        ],
                    }
                }
            },
        ]
    )
    client._post_graphql = lambda query, variables: next(responses)

    reports = client.fetch_reports(zone_id=73, encounter_id=103, limit=2, page_size=2)
    assert [report["code"] for report in reports] == ["B", "C"]


def test_fetch_events_uses_next_page_timestamp_for_pagination():
    client = FFLogsGraphQLClient("id", "secret")
    calls = []

    def fake_post(query, variables):
        calls.append(variables["startTime"])
        if len(calls) == 1:
            return {
                "reportData": {
                    "report": {
                        "events": {
                            "data": [{"timestamp": 1000}],
                            "nextPageTimestamp": 1500,
                        }
                    }
                }
            }
        return {
            "reportData": {
                "report": {
                    "events": {
                        "data": [{"timestamp": 1500}],
                        "nextPageTimestamp": None,
                    }
                }
            }
        }

    client._post_graphql = fake_post
    events = client.fetch_events(
        report_code="ABC123",
        fight_id=5,
        start_time=1000,
        end_time=2000,
    )

    assert calls == [1000.0, 1500.0]
    assert [event["timestamp"] for event in events] == [1000, 1500]


def test_fetch_report_details_queries_player_details_with_fight_ids():
    client = FFLogsGraphQLClient("id", "secret")
    calls = []

    def fake_post(query, variables):
        calls.append((query, variables))
        if query == FETCH_REPORT_DETAILS_QUERY:
            return {
                "reportData": {
                    "report": {
                        "code": "ABC123",
                        "title": "AAC Heavyweight",
                        "startTime": 1000,
                        "endTime": 5000,
                        "masterData": {
                            "actors": [{"id": 1, "name": "Tank"}],
                            "abilities": [{"gameID": 1, "name": "Crown of Arcadia"}],
                        },
                        "fights": [
                            {"id": 10, "kill": True},
                            {"id": 11, "kill": True},
                        ],
                    }
                }
            }
        if query == FETCH_PLAYER_DETAILS_QUERY:
            return {
                "reportData": {
                    "report": {
                        "playerDetails": {
                            "tanks": [{"name": "Tank One", "combatantInfo": {"hitPoints": 220000}}],
                            "healers": [{"name": "Healer One", "combatantInfo": {"hitPoints": 160000}}],
                        }
                    }
                }
            }
        raise AssertionError(f"Unexpected query: {query}")

    client._post_graphql = fake_post

    details = client.fetch_report_details("ABC123", 103)

    assert details["code"] == "ABC123"
    assert details["playerDetails"]["tanks"][0]["combatantInfo"]["hitPoints"] == 220000
    assert calls[1][0] == FETCH_PLAYER_DETAILS_QUERY
    assert calls[1][1]["fightIds"] == [10, 11]


def test_fetch_report_details_ignores_player_detail_failures():
    client = FFLogsGraphQLClient("id", "secret")

    def fake_post(query, variables):
        if query == FETCH_REPORT_DETAILS_QUERY:
            return {
                "reportData": {
                    "report": {
                        "code": "ABC123",
                        "title": "AAC Heavyweight",
                        "startTime": 1000,
                        "endTime": 5000,
                        "masterData": {"actors": [], "abilities": []},
                        "fights": [{"id": 10, "kill": True}],
                    }
                }
            }
        if query == FETCH_PLAYER_DETAILS_QUERY:
            raise ValueError("fightIDs required")
        raise AssertionError(f"Unexpected query: {query}")

    client._post_graphql = fake_post

    details = client.fetch_report_details("ABC123", 103)

    assert details["code"] == "ABC123"
    assert details["playerDetails"] == {}


def test_queries_request_translated_english_names():
    assert "translate: true" in FETCH_REPORTS_PAGE_QUERY
    assert "translate: true" in FETCH_REPORT_DETAILS_QUERY
    assert "translate: true" in FETCH_EVENTS_QUERY
    assert "translate: true" in FETCH_PLAYER_DETAILS_QUERY
