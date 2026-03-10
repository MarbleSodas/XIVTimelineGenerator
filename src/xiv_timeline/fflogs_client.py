"""FFLogs API v2 Client for fetching damage data."""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, ConfigDict
import os

logger = logging.getLogger("xiv_timeline.fflogs_client")

# FFLogs API v2 Base URLs
FFLOGS_AUTH_URL = "https://www.fflogs.com/oauth/token"
FFLOGS_API_URL = "https://www.fflogs.com/api/v2/client"


class DamageStat(BaseModel):
    """Summarized damage statistics for an ability."""
    ability_name: str
    ability_id: int
    count: int
    # Cross-report damage statistics
    unmitigated_damage_70th: float
    damage_min: float = 0.0
    damage_max: float = 0.0
    damage_median: float = 0.0
    damage_samples: int = 0
    # Classification
    ability_type: Optional[str] = None
    is_dot: bool = False
    # Enriched fields for mitigation planning
    target_count_avg: float = 0.0
    cast_duration: Optional[float] = None
    ability_game_id: Optional[str] = None  # hex ID for cactbot cross-reference
    model_config = ConfigDict(extra="allow")

class FFLogsClient:
    """Client for querying the FFLogs v2 GraphQL API."""

    def __init__(self) -> None:
        self.client_id = os.environ.get("FFLOGS_CLIENT_ID")
        self.client_secret = os.environ.get("FFLOGS_CLIENT_SECRET")
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _authenticate(self) -> None:
        """Fetch an OAuth2 token using client credentials."""
        if not self.client_id or not self.client_secret:
            raise ValueError("FFLOGS_CLIENT_ID or FFLOGS_CLIENT_SECRET not set in environment.")

        if self._access_token and self._token_expiry and datetime.now() < self._token_expiry:
            return

        logger.info("[fflogs] Authenticating with FFLogs v2 API...")
        response = await self.client.post(
            FFLOGS_AUTH_URL,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
        )
        response.raise_for_status()
        data = response.json()
        
        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 86400)
        self._token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)
        logger.info("[fflogs] Authentication successful.")

    async def query_graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against the FFLogs API."""
        await self._authenticate()
        
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = await self.client.post(FFLOGS_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if "errors" in result:
            logger.error(f"[fflogs] GraphQL Errors: {result['errors']}")
            raise ValueError(f"GraphQL Query Failed: {result['errors'][0]['message']}")
            
        return result["data"]

    async def get_top_reports(self, encounter_id: int, limit: int = 10) -> List[str]:
        """Get top parse report codes for a given encounter.
        
        Fetches up to `limit` unique report codes from FFLogs rankings.
        """
        query = """
        query($encounterId: Int!) {
            worldData {
                encounter(id: $encounterId) {
                    fightRankings(page: 1)
                }
            }
        }
        """
        try:
            data = await self.query_graphql(query, {"encounterId": encounter_id})
            # Navigate nested response safely
            data = data or {}
            world_data = data.get("worldData") or {}
            encounter = world_data.get("encounter") or {}
            rankings = encounter.get("fightRankings") or {}
            
            if isinstance(rankings, str):
                import json
                rankings = json.loads(rankings)
                
            rankings_list = rankings.get("rankings", [])
            report_codes = []
            
            for rank in rankings_list:
                report = rank.get("report", {})
                code = report.get("code")
                if code and code not in report_codes:
                    report_codes.append(code)
                    if len(report_codes) >= limit:
                        break
                    
            logger.info(f"[fflogs] Found {len(report_codes)} top reports for encounter {encounter_id}")
            return report_codes
        except Exception as e:
            logger.error(f"[fflogs] Error fetching top reports: {e}")
            return []

    async def get_damage_events(self, report_code: str, fight_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch damage taken events from an encounter.
        We request unmitigatedAmount.
        """
        # First query: find the correct fightId if not provided
        if not fight_id:
            fight_query = """
            query($code: String!) {
                reportData {
                    report(code: $code) {
                        fights(killType: Kills) {
                            id
                            startTime
                            endTime
                        }
                    }
                }
            }
            """
            data = await self.query_graphql(fight_query, {"code": report_code})
            fights = data.get("reportData", {}).get("report", {}).get("fights", [])
            if not fights:
                return []
            
            # Use the first full clear
            fight = fights[0]
            fight_id = fight["id"]
            start_time = fight["startTime"]
            end_time = fight["endTime"]
        else:
            pass

        # Fetch damage-taken table (summary) for the fight
        table_query = """
        query($code: String!, $fightId: Int!) {
            reportData {
                report(code: $code) {
                    table(fightIDs: [$fightId], dataType: DamageTaken, viewBy: Ability)
                }
            }
        }
        """
        
        try:
            data = await self.query_graphql(table_query, {"code": report_code, "fightId": fight_id})
            table_data = data.get("reportData", {}).get("report", {}).get("table", {})
            
            if not table_data or not table_data.get("data"):
                return []
                
            entries = table_data.get("data", {}).get("entries", [])
            return entries
        except Exception as e:
            logger.error(f"[fflogs] Error fetching damage events for report {report_code}: {e}")
            return []

    async def get_fight_cast_events(self, report_code: str, fight_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch enemy cast events (completed casts only, no begincast) for cast duration data.
        
        Filters out begincast (type=0) to only keep completed casts (type=1/damage).
        """
        # First get fight details
        if not fight_id:
            fight_query = """
            query($code: String!) {
                reportData {
                    report(code: $code) {
                        fights(killType: Kills) {
                            id
                            startTime
                            endTime
                        }
                    }
                }
            }
            """
            data = await self.query_graphql(fight_query, {"code": report_code})
            fights = data.get("reportData", {}).get("report", {}).get("fights", [])
            if not fights:
                return []
            fight = fights[0]
            fight_id = fight["id"]
            start_time = fight["startTime"]
            end_time = fight["endTime"]
        else:
            # If fight_id is given, we need to fetch start/end times
            fight_query = """
            query($code: String!, $fightId: Int!) {
                reportData {
                    report(code: $code) {
                        fights(fightIDs: [$fightId]) {
                            id
                            startTime
                            endTime
                        }
                    }
                }
            }
            """
            data = await self.query_graphql(fight_query, {"code": report_code, "fightId": fight_id})
            fights = data.get("reportData", {}).get("report", {}).get("fights", [])
            if not fights:
                return []
            fight = fights[0]
            start_time = fight["startTime"]
            end_time = fight["endTime"]

        # Fetch cast events from enemies (hostilityType: Enemies)
        # dataType: Casts gives us cast start + cast end events
        events_query = """
        query($code: String!, $startTime: Float!, $endTime: Float!, $fightId: Int!) {
            reportData {
                report(code: $code) {
                    events(
                        fightIDs: [$fightId]
                        startTime: $startTime
                        endTime: $endTime
                        dataType: Casts
                        hostilityType: Enemies
                        limit: 10000
                    ) {
                        data
                        nextPageTimestamp
                    }
                }
            }
        }
        """
        
        all_events = []
        current_start = start_time
        
        try:
            # Paginate through all events
            while current_start is not None and current_start < end_time:
                data = await self.query_graphql(events_query, {
                    "code": report_code,
                    "fightId": fight_id,
                    "startTime": current_start,
                    "endTime": end_time,
                })
                
                events_data = data.get("reportData", {}).get("report", {}).get("events", {})
                events = events_data.get("data", [])
                next_page = events_data.get("nextPageTimestamp")
                
                # Filter: only keep "cast" type events (type != "begincast")
                # In FFLogs events, begincast has type="begincast", cast completion has type="cast"
                for event in events:
                    event_type = event.get("type", "")
                    if event_type == "begincast":
                        continue  # Skip cast starts per user request
                    all_events.append(event)
                
                if next_page and next_page > current_start:
                    current_start = next_page
                else:
                    break
                    
            logger.info(f"[fflogs] Fetched {len(all_events)} cast events for report {report_code}")
            return all_events
        except Exception as e:
            logger.error(f"[fflogs] Error fetching cast events for report {report_code}: {e}")
            return []

    def _extract_cast_durations(self, cast_events: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract average cast durations from cast events.
        
        Pairs begincast → cast events to compute cast bar duration.
        Returns dict of ability_name → average_cast_duration_seconds.
        """
        # Cast events come as pairs: begincast then cast
        # We track begincast timestamps and match them with the next cast for the same ability
        # Since we filtered begincast out, we need a different approach:
        # We actually need both begincast AND cast to compute duration.
        # Let's refine: we'll accept all events here and filter in the caller.
        
        # For now, we can estimate cast duration from the cactbot data which has "duration" field.
        # If cast events are available with both types, pair them.
        
        cast_starts: Dict[int, float] = {}  # abilityGameID → timestamp
        durations: Dict[str, List[float]] = {}  # ability_name → list of durations
        
        for event in cast_events:
            ability = event.get("ability", {})
            game_id = ability.get("guid", 0)
            name = ability.get("name", "")
            timestamp = event.get("timestamp", 0)
            event_type = event.get("type", "")
            
            if event_type == "begincast":
                cast_starts[game_id] = timestamp
            elif event_type == "cast" and game_id in cast_starts:
                duration_ms = timestamp - cast_starts[game_id]
                duration_s = duration_ms / 1000.0
                if 0.5 < duration_s < 30:  # Reasonable cast bar duration
                    if name not in durations:
                        durations[name] = []
                    durations[name].append(duration_s)
                del cast_starts[game_id]
        
        # Average the durations
        result = {}
        for name, dur_list in durations.items():
            if dur_list:
                result[name] = statistics.median(dur_list)
        
        return result

    def clean_and_aggregate_damage(self, all_entries: List[List[Dict[str, Any]]]) -> Dict[str, DamageStat]:
        """
        Clean and aggregate damage across multiple reports (up to 10).
        Computes min/max/median/70th percentile of unmitigated damage.
        Removes 'attack' and common non-damaging casts.
        """
        ability_data: Dict[str, List[float]] = {}
        ability_ids: Dict[str, int] = {}
        ability_metadata: Dict[str, Dict[str, Any]] = {}
        
        for entries in all_entries:
            for entry in entries:
                name = entry.get("name", "")
                ab_id = entry.get("guid", 0)
                
                # Filter out basic attacks and environment
                if not name or "attack" in name.lower() or name.lower() in ["unknown", "environment"]:
                    continue
                    
                total_hits = entry.get("hitCount", 0)
                if total_hits <= 0:
                    continue
                    
                total_damage = entry.get("total", 0)
                unmitigated_damage = entry.get("unmitigatedTotal", total_damage)
                
                if unmitigated_damage <= 0:
                    continue
                    
                # Per-hit damage
                per_hit = unmitigated_damage / total_hits
                
                if name not in ability_data:
                    ability_data[name] = []
                    ability_metadata[name] = {
                        "targets": set(),
                        "uses": 0,
                        "hitCount": 0,
                        "tickCount": 0,
                        "target_counts": [],  # per-report target counts
                    }
                
                ability_data[name].append(per_hit)
                ability_ids[name] = ab_id
                
                # Update metadata
                ability_metadata[name]["uses"] += entry.get("uses", 0)
                ability_metadata[name]["hitCount"] += total_hits
                ability_metadata[name]["tickCount"] += entry.get("tickCount", 0)
                
                # Track targets for classification
                targets_in_entry = entry.get("targets", [])
                target_types = set()
                for tgt in targets_in_entry:
                    if tgt.get("type"):
                        ability_metadata[name]["targets"].add(tgt.get("type"))
                        target_types.add(tgt.get("type"))
                
                # Track target count per report entry
                if targets_in_entry:
                    ability_metadata[name]["target_counts"].append(len(targets_in_entry))
                
        # Calculate stats
        results = {}
        for name, damages in ability_data.items():
            if not damages:
                continue
                
            damages.sort()
            
            # Min/Max/Median/70th-percentile
            damage_min = damages[0]
            damage_max = damages[-1]
            damage_median = statistics.median(damages)
            
            if len(damages) > 1:
                idx_70 = int((len(damages) - 1) * 0.7)
                percentile_70 = damages[idx_70]
            else:
                percentile_70 = damages[0]
                
            # Discard anything insanely small
            if percentile_70 < 500:
                continue
                
            # Heuristics for ability type and DOT
            meta = ability_metadata[name]
            is_dot = meta["tickCount"] > 0
            
            uses = meta["uses"]
            hits = meta["hitCount"]
            targets = meta["targets"]
            target_counts = meta["target_counts"]
            
            # Average target count
            target_count_avg = statistics.mean(target_counts) if target_counts else 0.0
            
            ability_type = None
            if uses > 0:
                hits_per_use = hits / uses
                
                if hits_per_use >= 7:
                    ability_type = "Raidwide"
                elif 4 <= hits_per_use < 7:
                    ability_type = "Party Stack"
                elif hits_per_use <= 2.5:
                    tank_jobs = {"DarkKnight", "Paladin", "Warrior", "Gunbreaker"}
                    if targets and targets.issubset(tank_jobs):
                        ability_type = "Tankbuster"
                    elif len(targets) >= 8 and hits_per_use <= 1.5:
                        ability_type = "Spread"
                    elif hits_per_use <= 1.5 and percentile_70 > damage_median * 2:
                        # High single-target damage, likely tankbuster even if not exclusively on tanks
                        ability_type = "Tankbuster"
                
                # Cross-validate with ability name patterns
                name_lower = name.lower()
                if any(kw in name_lower for kw in ["buster", "cleave", "fracture", "sting"]):
                    if ability_type is None:
                        ability_type = "Tankbuster"
                elif any(kw in name_lower for kw in ["enrage", "rotten heart"]):
                    ability_type = "Enrage"
                
            # Convert ability_id to hex for cactbot cross-reference
            ab_id = ability_ids.get(name, 0)
            game_id_hex = f"{ab_id:04X}" if ab_id else None
                
            results[name] = DamageStat(
                ability_name=name,
                ability_id=ab_id,
                count=len(damages),
                unmitigated_damage_70th=percentile_70,
                damage_min=damage_min,
                damage_max=damage_max,
                damage_median=damage_median,
                damage_samples=len(damages),
                ability_type=ability_type,
                is_dot=is_dot,
                target_count_avg=target_count_avg,
                ability_game_id=game_id_hex,
            )
            
        return results

    async def get_boss_damage_values(self, encounter_id: int) -> Dict[str, DamageStat]:
        """High-level method to fetch and clean boss damage values across 10 reports."""
        reports = await self.get_top_reports(encounter_id, limit=10)
        if not reports:
            return {}
            
        all_entries = []
        for code in reports:
            entries = await self.get_damage_events(code)
            if entries:
                all_entries.append(entries)
                
        return self.clean_and_aggregate_damage(all_entries)

    async def close(self) -> None:
        await self.client.aclose()
