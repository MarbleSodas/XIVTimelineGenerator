from typing import List, Dict, Any, Optional, Tuple
import re
from schemas.aggregation_schemas import (
    AggregatedAction,
    DamageThresholds,
    AggregationInput,
    AggregationOutput,
)
from schemas.cactbot_schemas import CactbotTimelineEntry
from schemas.damage_schemas import DamageEvent
from tools.statistics import (
    cluster_by_proximity,
    filter_outliers_iqr,
    median,
    std_dev,
    calculate_damage_thresholds,
    get_most_common,
    normalize_action_name,
    fuzzy_match,
)


class TimelineAggregatorAgent:
    def __init__(self):
        self.name = "TimelineAggregatorAgent"
        self.description = "Aggregates damage values from FFLogs for cactbot timeline entries"
    
    def run(
        self,
        damage_events: List[DamageEvent],
        cactbot_timeline: List[CactbotTimelineEntry],
        iqr_multiplier: float = 1.5,
        occurrence_gap_seconds: float = 15.0,
    ) -> AggregationOutput:
        if not cactbot_timeline:
            return AggregationOutput(
                aggregated_actions=[],
                damage_thresholds=DamageThresholds(),
                tank_buster_count=0,
                raidwide_count=0,
            )
        
        cactbot_map = self._build_cactbot_map(cactbot_timeline)
        
        sync_offset = self._calculate_sync_offset(damage_events, cactbot_timeline)
        
        adjusted_events = [
            e.model_copy(update={"timestamp": e.timestamp - sync_offset})
            for e in damage_events
        ]
        
        events_by_action = self._group_events_by_action(adjusted_events)
        all_fflogs_events = adjusted_events
        
        total_reports = len(set(e.report_code for e in damage_events))
        
        all_damages = [float(e.unmitigated_damage) for e in damage_events]
        thresholds = {
            "p50": sorted(all_damages)[len(all_damages) // 2] if all_damages else 0,
            "p75": sorted(all_damages)[int(len(all_damages) * 0.75)] if all_damages else 0,
            "p90": sorted(all_damages)[int(len(all_damages) * 0.90)] if all_damages else 0,
        }
        
        aggregated_actions = []
        
        # Group cactbot entries by normalized name to consolidate multiple hits
        # This ensures abilities with multiple hits over time appear as one action with time_range
        entry_groups: Dict[str, List[Dict[str, Any]]] = {}
        
        for entry in cactbot_timeline:
            if entry.is_commented:
                continue
            
            base_name = entry.original_name if entry.original_name else entry.name
            
            if "(cast)" in base_name.lower():
                continue
            
            name_lower = base_name.lower()
            if name_lower.startswith("--") or name_lower in ["--sync--", "--jump", "--middle--"]:
                continue
            
            clean_name = base_name
            for suffix in ["(damage)", "(cast)", "(first)", "(second)", "(jump)", "(jump end)"]:
                clean_name = clean_name.replace(f" {suffix}", "").replace(f"{suffix}", "")
            clean_name = clean_name.strip()
            
            normalized = normalize_action_name(re.sub(r'\([^)]*\)', '', clean_name).strip())
            
            # Group by normalized name (not by individual entry)
            if normalized not in entry_groups:
                entry_groups[normalized] = []
            
            entry_groups[normalized].append({
                "entry": entry,
                "clean_name": clean_name,
                "normalized": normalized,
            })
        
        # Process each group
        for normalized, group_entries in entry_groups.items():
            if not group_entries:
                continue
            
            # Get matching events for this ability
            matching_events = events_by_action.get(normalized, [])
            
            # Get the first entry for this ability (use its time as base)
            first_entry_data = group_entries[0]
            first_entry = first_entry_data["entry"]
            clean_name = first_entry_data["clean_name"]
            
            # Calculate occurrence based on how many times this ability appears in timeline
            entry_occurrence = self._get_occurrence_number(cactbot_timeline, first_entry, normalized)
            
            # Get all times for this ability from the group
            all_group_times = [e["entry"].time for e in group_entries]
            min_time = min(all_group_times)
            max_time = max(all_group_times)
            
            # Multi-hit: only if entries are within 10 seconds of each other (consecutive)
            sorted_times = sorted(all_group_times)
            time_span = sorted_times[-1] - sorted_times[0] if len(sorted_times) > 1 else 0
            is_multi_hit = len(group_entries) > 1 and time_span <= 10.0
            
            window_start = min_time - 10
            window_end = max_time + 10
            
            occ_events = [
                e for e in matching_events
                if window_start <= e.timestamp <= window_end
            ]
            
            if not occ_events:
                occ_events = self._find_events_by_timing_and_damage(
                    all_fflogs_events, min_time, normalized, thresholds
                )
            
            if not occ_events:
                continue
            
            damages = [float(e.unmitigated_damage) for e in occ_events]
            filtered_damages, _ = filter_outliers_iqr(damages, iqr_multiplier)
            
            target_counts = [float(len(set(e.target_id for e in occ_events)))]
            damage_types = [e.damage_type for e in occ_events]
            dominant_damage_type = get_most_common(damage_types) if damage_types else "physical"
            
            damage = median(filtered_damages) if filtered_damages else 0
            target_count = median(target_counts)
            
            is_tank_buster = self._detect_tank_buster(
                clean_name, damage, target_count, thresholds
            )
            is_raidwide = self._detect_raidwide(target_count, occ_events, min_time)
            is_dual = is_tank_buster and 1.5 <= target_count <= 2.5
            
            importance = self._determine_importance(damage, is_tank_buster, thresholds)
            
            action_id = (
                clean_name.lower()
                .replace(" ", "_")
                .replace("'", "")
                .replace("(", "")
                .replace(")", "") +
                f"_{entry_occurrence}"
            )
            
            # Set time_range for multi-hit abilities
            time_range = None
            if is_multi_hit:
                time_range = (round(min_time, 1), round(max_time, 1))
            else:
                # Check cactbot map for consecutive ranges
                cactbot_data = cactbot_map.get(normalized, {})
                consecutive_ranges = cactbot_data.get("consecutive_ranges", [])
                for range_start, range_end in consecutive_ranges:
                    if min_time >= range_start and min_time <= range_end:
                        time_range = (round(range_start, 1), round(range_end, 1))
                        break
            
            unique_reports = len(set(e.report_code for e in occ_events))
            report_ratio = unique_reports / total_reports if total_reports > 0 else 1.0
            
            aggregated_actions.append(AggregatedAction(
                id=action_id,
                name=clean_name.title(),
                time=round(min_time, 1),
                occurrence=entry_occurrence,
                unmitigated_damage=self._format_damage(damage),
                damage_type=dominant_damage_type,
                target_count_median=target_count,
                target_count_std_dev=0,
                importance=importance,
                is_tank_buster=is_tank_buster,
                is_dual_tank_buster=is_dual,
                is_raidwide=is_raidwide,
                time_range=time_range,
                report_ratio=report_ratio,
                hit_count=len(group_entries) if is_multi_hit else None,
            ))
        
        aggregated_actions.sort(key=lambda a: a.time)
        
        tank_buster_count = sum(1 for a in aggregated_actions if a.is_tank_buster)
        raidwide_count = len(aggregated_actions) - tank_buster_count
        immediate_raidwide_count = sum(1 for a in aggregated_actions if a.is_raidwide)
        
        return AggregationOutput(
            aggregated_actions=aggregated_actions,
            damage_thresholds=DamageThresholds(**thresholds),
            tank_buster_count=tank_buster_count,
            raidwide_count=raidwide_count,
            immediate_raidwide_count=immediate_raidwide_count,
        )
    
    def _find_events_by_timing_and_damage(
        self,
        all_events: List[DamageEvent],
        cactbot_time: float,
        cactbot_name: str,
        thresholds: Dict[str, float],
    ) -> List[DamageEvent]:
        window_start = cactbot_time - 10
        window_end = cactbot_time + 10
        
        candidates = [e for e in all_events if window_start <= e.timestamp <= window_end]
        
        if not candidates:
            return []
        
        best_match = None
        best_score = -1
        
        fflogs_names = set(normalize_action_name(e.ability_name) for e in candidates)
        
        for event in candidates:
            event_name = normalize_action_name(event.ability_name)
            
            name_score = 0
            if fuzzy_match(event_name, cactbot_name, threshold=0.6):
                name_score = 1.0
            elif event_name in cactbot_name or cactbot_name in event_name:
                name_score = 0.8
            
            damage_score = 0
            damage = float(event.unmitigated_damage)
            if damage >= thresholds.get("p90", 0):
                damage_score = 0.5
            elif damage >= thresholds.get("p75", 0):
                damage_score = 0.3
            
            total_score = name_score + damage_score
            
            if total_score > best_score:
                best_score = total_score
                best_match = event
        
        if best_match and best_score > 0:
            return [e for e in candidates if normalize_action_name(e.ability_name) == normalize_action_name(best_match.ability_name)]
        
        return []
    
    def _get_occurrence_number(
        self,
        timeline: List[CactbotTimelineEntry],
        current_entry: CactbotTimelineEntry,
        normalized_name: str,
    ) -> int:
        count = 0
        for entry in timeline:
            # Skip commented entries
            if entry.is_commented:
                continue
            
            # Skip cast entries (only count damage entries)
            base_name = entry.original_name if entry.original_name else entry.name
            if "(cast)" in base_name.lower():
                continue
            
            # Check if this is the current entry
            if entry.time == current_entry.time and entry.name == current_entry.name:
                count += 1
                break
            
            # Count matching entries
            base_name_clean = re.sub(r'\s*\([^)]*\)', '', base_name).strip()
            if normalize_action_name(base_name_clean) == normalized_name:
                count += 1
        return max(1, count)
    
    def _calculate_sync_offset(
        self,
        events: List[DamageEvent],
        cactbot_timeline: List[CactbotTimelineEntry],
    ) -> float:
        if not events:
            return 0.0
        
        timeline_entries = []
        for entry in cactbot_timeline:
            if entry.is_commented:
                continue
            base_name = entry.original_name if entry.original_name else entry.name
            if "(cast)" in base_name.lower():
                continue
            
            name_lower = base_name.lower()
            if name_lower.startswith("--") or name_lower in ["--sync--", "--jump", "--middle--"]:
                continue
            
            normalized = normalize_action_name(re.sub(r'\s*\([^)]*\)', '', base_name).strip())
            timeline_entries.append((entry.time, normalized, base_name))
        
        if not timeline_entries:
            return 0.0
        
        events_by_action = self._group_events_by_action(events)
        
        best_offset = 0.0
        best_match_count = 0
        
        for cactbot_time, cactbot_name, original_name in timeline_entries[:10]:
            for name_key, name_events in events_by_action.items():
                if fuzzy_match(name_key, cactbot_name, threshold=0.5):
                    times = [e.timestamp for e in name_events]
                    if times:
                        offset = times[0] - cactbot_time
                        
                        match_count = sum(
                            1 for e in name_events
                            if abs(e.timestamp - cactbot_time - offset) < 15
                        )
                        
                        if match_count > best_match_count:
                            best_match_count = match_count
                            best_offset = offset
        
        if best_match_count > 0:
            return best_offset
        
        candidates = sorted(events, key=lambda e: e.timestamp)
        if candidates and timeline_entries:
            return candidates[0].timestamp - timeline_entries[0][0]
        
        return 0.0
    
    def _build_cactbot_map(
        self,
        cactbot_timeline: List[CactbotTimelineEntry],
    ) -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        
        for entry in cactbot_timeline:
            name = entry.name
            time = entry.time
            
            # Use original_name if available, otherwise clean up the name
            if entry.original_name:
                base_name = entry.original_name
            else:
                # Remove suffixes like (damage), (First), (Second), (jump), etc.
                base_name = name
                for suffix in ["(damage)", "(cast)", "(First)", "(Second)", "(jump)", "(jump end)"]:
                    base_name = base_name.replace(f" {suffix}", "").replace(f"{suffix}", "")
                base_name = base_name.strip()
            
            # Normalize for matching
            normalized = normalize_action_name(base_name)
            
            if normalized not in result:
                result[normalized] = {
                    "cast_time": None,
                    "damage_times": [],
                    "all_times": [],
                    "consecutive_ranges": [],  # NEW: tracks consecutive hit groups
                }
            
            result[normalized]["all_times"].append(time)
            
            # Check if this is a cast entry
            if "(cast)" in name.lower() or entry.is_commented:
                if result[normalized]["cast_time"] is None:
                    result[normalized]["cast_time"] = time
            else:
                result[normalized]["damage_times"].append(time)
        
        # Calculate time ranges and consecutive hit groups
        for name, data in result.items():
            if data["damage_times"]:
                data["first_hit"] = min(data["damage_times"])
                data["last_hit"] = max(data["damage_times"])
                
                # Find consecutive hit groups (hits within 10 seconds of each other)
                sorted_times = sorted(data["damage_times"])
                consecutive_ranges = []
                if sorted_times:
                    current_range = [sorted_times[0]]
                    for i in range(1, len(sorted_times)):
                        # If gap is less than 10 seconds, consider it consecutive
                        if sorted_times[i] - sorted_times[i-1] < 10.0:
                            current_range.append(sorted_times[i])
                        else:
                            # Close current range and start new one
                            if len(current_range) > 1:  # Only track if 2+ consecutive hits
                                consecutive_ranges.append((min(current_range), max(current_range)))
                            current_range = [sorted_times[i]]
                    # Don't forget the last range
                    if len(current_range) > 1:
                        consecutive_ranges.append((min(current_range), max(current_range)))
                
                data["consecutive_ranges"] = consecutive_ranges
            elif data["all_times"]:
                data["first_hit"] = min(data["all_times"])
                data["last_hit"] = max(data["all_times"])
        
        return result
    
    def _group_events_by_action(
        self,
        events: List[DamageEvent],
    ) -> Dict[str, List[DamageEvent]]:
        grouped: Dict[str, List[DamageEvent]] = {}
        
        for event in events:
            key = normalize_action_name(event.ability_name)
            
            if key not in grouped:
                grouped[key] = []
            
            grouped[key].append(event)
        
        return grouped
    
    def _cluster_occurrences(
        self,
        events_by_action: Dict[str, List[DamageEvent]],
        gap_seconds: float,
    ) -> List[Dict[str, Any]]:
        occurrences = []
        
        for action_name, events in events_by_action.items():
            times = [e.timestamp for e in events]
            clusters = cluster_by_proximity(times, gap_seconds)
            
            for cluster_idx, cluster in enumerate(clusters):
                cluster_events = [
                    e for e in events
                    if cluster["min"] <= e.timestamp <= cluster["max"]
                ]
                
                damages = [float(e.unmitigated_damage) for e in cluster_events]
                filtered_damages, _ = filter_outliers_iqr(damages, 1.5)
                
                target_ids = list(set(e.target_id for e in cluster_events))
                target_counts = [float(len(target_ids))]
                
                damage_types = [e.damage_type for e in cluster_events]
                dominant_damage_type = get_most_common(damage_types)
                
                occurrences.append({
                    "action_name": action_name,
                    "occurrence": cluster_idx + 1,
                    "times": cluster["values"],
                    "time": cluster["min"],
                    "median_damage": median(filtered_damages) if filtered_damages else 0,
                    "damage_type": dominant_damage_type,
                    "target_count_median": median(target_counts),
                    "target_count_std_dev": std_dev(target_counts),
                    "hit_count": len(cluster_events),
                })
        
        return sorted(occurrences, key=lambda o: o["time"])
    
    def _create_aggregated_action(
        self,
        occurrence: Dict[str, Any],
        thresholds: Dict[str, float],
        cactbot_map: Dict[str, Dict[str, Any]],
    ) -> AggregatedAction:
        name = occurrence["action_name"]
        damage = occurrence["median_damage"]
        damage_type = occurrence["damage_type"]
        target_count = occurrence.get("target_count_median", 8)
        
        is_tank_buster = self._detect_tank_buster(name, damage, target_count, thresholds)
        is_dual = is_tank_buster and 1.5 <= target_count <= 2.5
        
        importance = self._determine_importance(
            damage, is_tank_buster, thresholds
        )
        
        action_id = (
            name.lower()
            .replace(" ", "_")
            .replace("'", "")
            .replace("(", "")
            .replace(")", "") +
            f"_{occurrence['occurrence']}"
        )
        
        normalized = normalize_action_name(name)
        cactbot_data = cactbot_map.get(normalized, {})
        
        # Use consecutive ranges for time_range - only apply to abilities with 2+ consecutive hits
        time_range = None
        consecutive_ranges = cactbot_data.get("consecutive_ranges", [])
        if consecutive_ranges:
            # Find the range that contains this occurrence's time
            occ_time = occurrence["time"]
            for range_start, range_end in consecutive_ranges:
                if range_start <= occ_time <= range_end:
                    time_range = (round(range_start, 1), round(range_end, 1))
                    break
        
        return AggregatedAction(
            id=action_id,
            name=name.title(),
            time=round(occurrence["time"], 1),
            occurrence=occurrence["occurrence"],
            unmitigated_damage=self._format_damage(damage),
            damage_type=damage_type,
            target_count_median=target_count,
            target_count_std_dev=occurrence.get("target_count_std_dev", 0),
            importance=importance,
            is_tank_buster=is_tank_buster,
            is_dual_tank_buster=is_dual,
            time_range=time_range,
        )
    
    def _detect_tank_buster(
        self,
        name: str,
        damage: float,
        target_count: float,
        thresholds: Dict[str, float],
    ) -> bool:
        is_consistent = target_count >= 0.8 and target_count <= 2.5
        is_high_damage = damage >= thresholds.get("p75", 0)
        
        return is_consistent and is_high_damage
    
    def _detect_raidwide(
        self,
        target_count: float,
        events: List[DamageEvent],
        entry_time: float,
    ) -> bool:
        """
        Detect if an ability is a raidwide.
        
        A raidwide hits most/all party members (typically 6-8 targets).
        If hits happen over time (not immediate), this returns False but
        the time_range will be set to show the full duration.
        """
        # If most party members are hit, it's likely a raidwide
        if target_count >= 6.0:
            return True
        
        return False
    
    def _determine_importance(
        self,
        damage: float,
        is_tank_buster: bool,
        thresholds: Dict[str, float],
    ) -> str:
        if damage >= thresholds.get("p90", 0):
            return "critical"
        if is_tank_buster:
            return "high"
        if damage >= thresholds.get("p75", 0):
            return "high"
        if damage >= thresholds.get("p50", 0):
            return "medium"
        return "low"
    
    def _format_damage(self, damage: float) -> str:
        if damage >= 1000:
            return f"~{int(damage):,}"
        return str(int(damage))
