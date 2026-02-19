from typing import List, Dict, Optional, Any, Tuple
from schemas.variant_schemas import (
    TimelineBranch,
    TimelineVariant,
    VariantDetectionInput,
    VariantDetectionOutput,
)
from schemas.cactbot_schemas import CactbotTimelineEntry
from schemas.damage_schemas import DamageEvent
from tools.statistics import (
    cluster_by_proximity,
    normalize_action_name,
    median,
    get_most_common,
    fuzzy_match,
)


class TimelineVariantDetectorAgent:
    """
    Atomic agent for detecting timeline variants.
    
    Uses Cactbot timeline as the reference point to detect real variants:
    - For each cactbot timeline entry, check if FFLogs has matching ability at that time
    - If FFLogs shows DIFFERENT ability at expected time -> REAL variant
    - If FFLogs shows no matching ability -> missed/optional ability
    
    This approach dramatically reduces noise compared to time-bucket approach.
    """
    
    def __init__(self):
        self.name = "TimelineVariantDetectorAgent"
        self.description = "Identifies timeline branches using cactbot as reference"
    
    def run(
        self,
        damage_events_by_report: Dict[str, List[DamageEvent]],
        cactbot_timeline: List[CactbotTimelineEntry],
        match_time_window: float = 5.0,
        min_occurrence_ratio: float = 0.3,
    ) -> VariantDetectionOutput:
        """
        Detect timeline variants using cactbot timeline as reference.
        
        Key logic:
        1. For each cactbot entry, find matching FFLogs events within time window
        2. Group FFLogs events by cactbot entry to find actual abilities used
        3. Identify where FFLogs differs from cactbot -> REAL variants
        4. Determine default timeline from cactbot + most common FFLogs match
        """
        # Match FFLogs events to cactbot timeline entries
        matched_events = self._match_fflogs_to_cactbot(
            damage_events_by_report, cactbot_timeline, match_time_window
        )
        
        # Find real variant points (where FFLogs differs from cactbot)
        variant_points = self._find_real_variants(
            matched_events, cactbot_timeline, min_occurrence_ratio
        )
        
        # Build default timeline from cactbot + most common matches
        default_timeline = self._build_default_timeline(
            matched_events, cactbot_timeline
        )
        
        # Identify complete action sequences (branches)
        branches = self._identify_branches(
            damage_events_by_report, cactbot_timeline, matched_events, min_occurrence_ratio
        )
        
        total_reports = len(damage_events_by_report)
        default_count = total_reports  # Simplified - all reports follow default
        default_coverage = 1.0 if total_reports > 0 else 0.0
        
        return VariantDetectionOutput(
            branches=branches,
            default_timeline=default_timeline,
            variant_points=variant_points,
            total_unique_timelines=len(branches),
            default_coverage=default_coverage,
        )
    
    def _match_fflogs_to_cactbot(
        self,
        events_by_report: Dict[str, List[DamageEvent]],
        cactbot_timeline: List[CactbotTimelineEntry],
        time_window: float,
    ) -> Dict[int, Dict[str, List[Tuple[str, str]]]]:
        """
        Match FFLogs events to cactbot timeline entries.
        
        Returns: Dict[cactbot_entry_index -> {fflogs_ability -> [(report_code, original_name)]}]
        """
        matched: Dict[int, Dict[str, List[Tuple[str, str]]]] = {}
        
        for entry_idx, entry in enumerate(cactbot_timeline):
            matched[entry_idx] = {}
            
            # Get expected abilities from cactbot (base_name + variants if present)
            expected_abilities = self._get_expected_abilities(entry)
            
            # Find FFLogs events within time window
            for report_code, events in events_by_report.items():
                for event in events:
                    # Check if event is within time window of cactbot entry
                    if abs(event.timestamp - entry.time) <= time_window:
                        ff_name = normalize_action_name(event.ability_name)
                        
                        # Check if this FFLogs ability matches any expected cactbot ability
                        matched_any = False
                        for expected in expected_abilities:
                            if fuzzy_match(ff_name, expected, threshold=0.7):
                                matched_any = True
                                break
                        
                        # Record the ability (whether it matched or not)
                        if ff_name not in matched[entry_idx]:
                            matched[entry_idx][ff_name] = []
                        matched[entry_idx][ff_name].append((report_code, event.ability_name))
        
        return matched
    
    def _get_expected_abilities(self, entry: CactbotTimelineEntry) -> List[str]:
        """Get list of expected abilities from cactbot entry."""
        abilities = []
        
        # Add base name
        if entry.base_name:
            abilities.append(normalize_action_name(entry.base_name))
        elif entry.name:
            abilities.append(normalize_action_name(entry.name))
        
        # Add variants if present
        if entry.variants:
            for variant in entry.variants:
                abilities.append(normalize_action_name(variant))
        
        return abilities
    
    def _find_real_variants(
        self,
        matched_events: Dict[int, Dict[str, List[Tuple[str, str]]]],
        cactbot_timeline: List[CactbotTimelineEntry],
        min_ratio: float,
    ) -> List[TimelineVariant]:
        """
        Find REAL variant points where FFLogs differs from cactbot expectation.
        
        A real variant exists when:
        - Cactbot expects ability X
        - FFLogs shows ability Y (different from X) at that time
        """
        variants: List[TimelineVariant] = []
        
        for entry_idx, entry in enumerate(cactbot_timeline):
            fflogs_abilities = matched_events.get(entry_idx, {})
            
            if not fflogs_abilities:
                continue
            
            # Get expected abilities from cactbot
            expected = self._get_expected_abilities(entry)
            
            # Categorize FFLogs abilities as "expected" vs "unexpected"
            expected_ff: Dict[str, int] = {}
            unexpected_ff: Dict[str, int] = {}
            
            for ff_name, occurrences in fflogs_abilities.items():
                count = len(occurrences)
                is_expected = any(fuzzy_match(ff_name, exp, 0.7) for exp in expected)
                
                if is_expected:
                    expected_ff[ff_name] = count
                else:
                    unexpected_ff[ff_name] = count
            
            # Only create variant if there are unexpected abilities
            if len(unexpected_ff) > 0:
                total = sum(expected_ff.values()) + sum(unexpected_ff.values())
                
                branches = []
                
                # Add expected branches (sorted by count)
                if expected_ff:
                    sorted_expected = sorted(expected_ff.items(), key=lambda x: x[1], reverse=True)
                    for idx, (action, count) in enumerate(sorted_expected):
                        branches.append(
                            TimelineBranch(
                                branch_id=f"variant_{entry_idx}_expected_{idx}",
                                description=action,
                                action_sequence=[action],
                                occurrence_count=count,
                                occurrence_ratio=count / total if total > 0 else 0,
                                is_default=(idx == 0 and len(unexpected_ff) == 0),
                            )
                        )
                
                # Add unexpected branches (these are REAL variants)
                if unexpected_ff:
                    sorted_unexpected = sorted(unexpected_ff.items(), key=lambda x: x[1], reverse=True)
                    for idx, (action, count) in enumerate(sorted_unexpected):
                        branches.append(
                            TimelineBranch(
                                branch_id=f"variant_{entry_idx}_unexpected_{idx}",
                                description=action,
                                action_sequence=[action],
                                occurrence_count=count,
                                occurrence_ratio=count / total if total > 0 else 0,
                                is_default=False,
                            )
                        )
                
                # Only add if we have multiple branches and ratio meets threshold
                if len(branches) > 1:
                    # Check if any branch meets min ratio
                    max_ratio = max(b.occurrence_ratio for b in branches)
                    if max_ratio >= min_ratio:
                        variants.append(
                            TimelineVariant(
                                branch_point_time=entry.time,
                                branch_point_name=entry.name,
                                branches=branches,
                            )
                        )
        
        return variants
    
    def _build_default_timeline(
        self,
        matched_events: Dict[int, Dict[str, List[Tuple[str, str]]]],
        cactbot_timeline: List[CactbotTimelineEntry],
    ) -> List[str]:
        """Build default timeline using cactbot as base + most common FFLogs match."""
        default_timeline = []
        
        for entry_idx, entry in enumerate(cactbot_timeline):
            fflogs_abilities = matched_events.get(entry_idx, {})
            
            if not fflogs_abilities:
                # No FFLogs data - use cactbot name
                default_timeline.append(normalize_action_name(entry.name))
                continue
            
            # Get most common FFLogs ability at this time point
            all_abilities = []
            for ability_list in fflogs_abilities.values():
                for _, original_name in ability_list:
                    all_abilities.append(normalize_action_name(original_name))
            
            if all_abilities:
                most_common = get_most_common(all_abilities)
                default_timeline.append(most_common)
            else:
                default_timeline.append(normalize_action_name(entry.name))
        
        return default_timeline
    
    def _identify_branches(
        self,
        events_by_report: Dict[str, List[DamageEvent]],
        cactbot_timeline: List[CactbotTimelineEntry],
        matched_events: Dict[int, Dict[str, List[Tuple[str, str]]]],
        min_ratio: float,
    ) -> List[TimelineBranch]:
        """
        Identify complete action sequences as branches.
        
        Uses cactbot timeline as the timeline structure and matches
        FFLogs events to build actual sequences.
        """
        if not cactbot_timeline:
            return []
        
        # Build sequences for each report based on cactbot timeline
        report_sequences: Dict[str, List[str]] = {}
        
        for report_code, events in events_by_report.items():
            sequence = []
            
            for entry_idx, entry in enumerate(cactbot_timeline):
                # Find what ability this report used at this time point
                matched = matched_events.get(entry_idx, {})
                
                if matched:
                    # Get the most common ability for this report at this time
                    ability = get_most_common(
                        [orig for lst in matched.values() for _, orig in lst 
                         if any(rc == report_code for rc, _ in lst)]
                    )
                    if ability:
                        sequence.append(ability)
                    else:
                        sequence.append(normalize_action_name(entry.name))
                else:
                    sequence.append(normalize_action_name(entry.name))
            
            if sequence:
                report_sequences[report_code] = sequence
        
        # Count unique sequences
        sequence_counts: Dict[str, int] = {}
        for seq in report_sequences.values():
            key = "|".join(seq)
            sequence_counts[key] = sequence_counts.get(key, 0) + 1
        
        total = len(report_sequences)
        if total == 0:
            return []
        
        # Sort by count and create branches
        sorted_sequences = sorted(
            sequence_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        branches = []
        for idx, (seq_key, count) in enumerate(sorted_sequences):
            ratio = count / total
            
            if ratio < min_ratio and idx > 0:
                continue
            
            branches.append(
                TimelineBranch(
                    branch_id=f"branch_{idx}",
                    description=seq_key.replace("|", " -> "),
                    action_sequence=seq_key.split("|"),
                    occurrence_count=count,
                    occurrence_ratio=ratio,
                    is_default=(idx == 0),
                )
            )
        
        return branches
