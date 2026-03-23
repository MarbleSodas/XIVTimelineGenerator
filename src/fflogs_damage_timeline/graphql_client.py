import os
from typing import Any, Optional

import requests

FFLOGS_API_URL = "https://www.fflogs.com/api/v2/client"
FFLOGS_TOKEN_URL = "https://www.fflogs.com/oauth/token"
REQUEST_TIMEOUT_SECONDS = 30
DEFAULT_REPORT_PAGE_SIZE = 25

FETCH_ZONE_ENCOUNTERS_QUERY = """
query ResolveEncounter($zoneId: Int!) {
  worldData {
    zone(id: $zoneId) {
      id
      name
      encounters {
        id
        name
      }
    }
  }
}
"""

FETCH_REPORTS_PAGE_QUERY = """
query GetReportsPage($zoneId: Int!, $page: Int!, $limit: Int!, $encounterId: Int!) {
  reportData {
    reports(
      zoneID: $zoneId
      page: $page
      limit: $limit
    ) {
      current_page
      has_more_pages
      data {
        code
        title
        startTime
        endTime
        fights(
          killType: Kills
          encounterID: $encounterId
          translate: true
        ) {
          id
          name
          kill
          difficulty
          encounterID
          startTime
          endTime
          friendlyPlayers
        }
      }
    }
  }
}
"""

FETCH_REPORT_DETAILS_QUERY = """
query GetReportDetails($reportCode: String!, $encounterId: Int!) {
  reportData {
    report(code: $reportCode) {
      code
      title
      startTime
      endTime
      masterData(translate: true) {
        actors {
          gameID
          id
          name
          server
          petOwner
          subType
          type
        }
        abilities {
          gameID
          name
          type
        }
      }
      fights(
        killType: Kills
        encounterID: $encounterId
        translate: true
      ) {
        id
        name
        kill
        difficulty
        encounterID
        startTime
        endTime
        friendlyPlayers
      }
    }
  }
}
"""

FETCH_EVENTS_QUERY = """
query GetDamageEvents($reportCode: String!, $fightId: Int!, $startTime: Float!, $endTime: Float!) {
  reportData {
    report(code: $reportCode) {
      events(
        dataType: DamageTaken
        fightIDs: [$fightId]
        startTime: $startTime
        endTime: $endTime
        hostilityType: Friendlies
        translate: true
        limit: 10000
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

    @staticmethod
    def _normalize_name(name: str) -> str:
        return " ".join(name.lower().split())

    def resolve_encounter_id(
        self,
        zone_id: int,
        boss_name: str,
        full_name: Optional[str] = None,
    ) -> int:
        data = self._post_graphql(FETCH_ZONE_ENCOUNTERS_QUERY, {"zoneId": zone_id})
        zone = (data.get("worldData") or {}).get("zone") or {}
        encounters = list(zone.get("encounters") or [])

        desired_names = {
            self._normalize_name(boss_name),
        }
        if full_name:
            desired_names.add(self._normalize_name(full_name))

        for encounter in encounters:
            encounter_name = self._normalize_name(encounter.get("name", ""))
            if encounter_name in desired_names:
                return int(encounter["id"])

        raise ValueError(
            f"Could not resolve encounter ID for '{boss_name}' in zone {zone_id}"
        )

    def fetch_reports(
        self,
        zone_id: int,
        encounter_id: int,
        limit: int,
        page_size: int = DEFAULT_REPORT_PAGE_SIZE,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            return []

        page = 1
        matched_reports: list[dict[str, Any]] = []
        per_page = max(1, min(page_size, 100))

        while len(matched_reports) < limit:
            data = self._post_graphql(
                FETCH_REPORTS_PAGE_QUERY,
                {
                    "zoneId": zone_id,
                    "page": page,
                    "limit": per_page,
                    "encounterId": encounter_id,
                },
            )
            reports_page = (data.get("reportData") or {}).get("reports") or {}
            page_reports = list(reports_page.get("data") or [])

            for report in page_reports:
                fights = [fight for fight in report.get("fights") or [] if fight.get("kill")]
                if not fights:
                    continue
                matched_reports.append({**report, "fights": fights})
                if len(matched_reports) >= limit:
                    break

            if len(matched_reports) >= limit:
                break
            if not reports_page.get("has_more_pages"):
                break
            page += 1

        return matched_reports[:limit]

    def fetch_report_details(
        self,
        report_code: str,
        encounter_id: int,
    ) -> Optional[dict[str, Any]]:
        data = self._post_graphql(
            FETCH_REPORT_DETAILS_QUERY,
            {
                "reportCode": report_code,
                "encounterId": encounter_id,
            },
        )
        report = (data.get("reportData") or {}).get("report")
        if report is None:
            return None

        fights = [fight for fight in report.get("fights") or [] if fight.get("kill")]
        master_data = report.get("masterData") or {}
        return {
            "code": report.get("code", report_code),
            "title": report.get("title", ""),
            "startTime": report.get("startTime"),
            "endTime": report.get("endTime"),
            "actors": list(master_data.get("actors") or []),
            "abilities": list(master_data.get("abilities") or []),
            "fights": fights,
        }

    def fetch_events(
        self,
        report_code: str,
        fight_id: int,
        start_time: float,
        end_time: float,
    ) -> list[dict[str, Any]]:
        all_events: list[dict[str, Any]] = []
        page_start_time = float(start_time)
        desired_end_time = float(end_time)

        while True:
            data = self._post_graphql(
                FETCH_EVENTS_QUERY,
                {
                    "reportCode": report_code,
                    "fightId": fight_id,
                    "startTime": page_start_time,
                    "endTime": desired_end_time,
                },
            )
            report = (data.get("reportData") or {}).get("report")
            if report is None:
                break

            events = report.get("events") or {}
            all_events.extend(events.get("data") or [])

            next_page = events.get("nextPageTimestamp")
            if next_page is None:
                break

            next_page_time = float(next_page)
            if next_page_time >= desired_end_time:
                break
            page_start_time = next_page_time

        return all_events
