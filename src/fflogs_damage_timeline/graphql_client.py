import os
from typing import Any, Optional

import requests

FFLOGS_API_URL = "https://www.fflogs.com/api/v2/client"
FFLOGS_TOKEN_URL = "https://www.fflogs.com/oauth/token"
REQUEST_TIMEOUT_SECONDS = 30

FETCH_REPORTS_QUERY = """
query GetKillReports($zoneId: Int!, $encounterId: Int!) {
  reportData {
    reports(
      zone: $zoneId
      boss: $encounterId
      difficulty: 101
      limit: 30
    ) {
      data {
        code
        title
        startTime
        endTime
      }
    }
  }
}
"""

FETCH_FIGHTS_QUERY = """
query GetKillFights($reportCode: String!, $encounterId: Int!) {
  reportData {
    report(code: $reportCode) {
      fights(
        killType: Kills
        encounterID: $encounterId
      ) {
        id
        startTime
        endTime
        encounterID
        difficulty
      }
    }
  }
}
"""

FETCH_EVENTS_QUERY = """
query GetDamageEvents($reportCode: String!, $fightId: Int!, $startTime: Float!, $endTime: Float!, $pageTimestamp: Float) {
  reportData {
    report(code: $reportCode) {
      code
      events(
        dataType: DamageTaken
        fightIDs: [$fightId]
        startTime: $startTime
        endTime: $endTime
        limit: 10000
        useAbilityIDs: false
        useActorIDs: false
        hostilityType: 0
      ) {
        data
        nextPageTimestamp
      }
    }
  }
}
"""


class FFLogsGraphQLClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self._client_id = client_id or os.environ.get("FFLOGS_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("FFLOGS_CLIENT_SECRET", "")
        self._token: Optional[str] = None

    def _ensure_token(self) -> str:
        if self._token is not None:
            return self._token

        if not self._client_id or not self._client_secret:
            raise ValueError("FFLogs client credentials are required")

        response = requests.post(
            FFLOGS_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        token = data["access_token"]
        self._token = token
        return token

    def _post_graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        token = self._ensure_token()
        response = requests.post(
            FFLOGS_API_URL,
            json={"query": query, "variables": variables},
            headers={"Authorization": f"Bearer {token}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            messages = "; ".join(
                error.get("message", "Unknown FFLogs API error")
                for error in payload["errors"]
            )
            raise ValueError(messages)
        return payload.get("data") or {}

    def fetch_reports(self, zone_id: int, encounter_id: int) -> list[dict[str, Any]]:
        data = self._post_graphql(
            FETCH_REPORTS_QUERY,
            {"zoneId": zone_id, "encounterId": encounter_id},
        )
        reports = (data.get("reportData") or {}).get("reports") or {}
        return list(reports.get("data") or [])

    def fetch_fights(self, report_code: str, encounter_id: int) -> list[dict[str, Any]]:
        data = self._post_graphql(
            FETCH_FIGHTS_QUERY,
            {"reportCode": report_code, "encounterId": encounter_id},
        )
        report = (data.get("reportData") or {}).get("report")
        if report is None:
            return []
        return list(report.get("fights") or [])

    def fetch_events(
        self,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
    ) -> list[dict[str, Any]]:
        all_events: list[dict[str, Any]] = []
        page_timestamp: Optional[float] = None

        while True:
            variables: dict[str, Any] = {
                "reportCode": report_code,
                "fightId": fight_id,
                "startTime": start_time,
                "endTime": end_time,
            }
            if page_timestamp is not None:
                variables["pageTimestamp"] = page_timestamp

            data = self._post_graphql(FETCH_EVENTS_QUERY, variables)
            report = (data.get("reportData") or {}).get("report")
            if report is None:
                break

            events = report.get("events") or {}
            page_events = events.get("data") or []
            all_events.extend(page_events)

            next_page = events.get("nextPageTimestamp")
            if next_page is None:
                break
            page_timestamp = float(next_page)

        return all_events
