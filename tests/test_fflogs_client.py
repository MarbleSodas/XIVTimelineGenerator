from fflogs_damage_timeline.graphql_client import (
    FFLogsGraphQLClient,
    FETCH_EVENTS_QUERY,
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


def test_queries_request_translated_english_names():
    assert "translate: true" in FETCH_REPORTS_PAGE_QUERY
    assert "translate: true" in FETCH_REPORT_DETAILS_QUERY
    assert "translate: true" in FETCH_EVENTS_QUERY
