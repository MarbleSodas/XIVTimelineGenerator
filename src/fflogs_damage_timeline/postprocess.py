"""Post-processing helpers for cleaned damage-event exports."""

from __future__ import annotations

from copy import deepcopy
from math import ceil
from statistics import median
from typing import Any
from collections import Counter

from fflogs_damage_timeline.normalizer import format_timestamp

TIMELINE_MERGE_WINDOW_MS = 1500
TIMELINE_STABILITY_THRESHOLD = 0.8
MIN_STRUCTURAL_SKIP_EVENTS = 2
MIN_STRUCTURAL_SKIP_DURATION_MS = 3000
DOT_GAP_TOLERANCE_MS = 4000
BRANCH_MERGE_MIN_RATIO_MIN = 0.9
BRANCH_MERGE_MIN_RATIO_MAX = 0.6
BRANCH_MERGE_MAX_SIGNIFICANT_RANGE_FRACTION = 0.2
CONTAINED_ROUTE_MIN_RATIO_MIN = 0.95
CONTAINED_ROUTE_MAX_SIGNIFICANT_RANGE_FRACTION = 0.2
BALANCED_BRANCH_MIN_REPORTS = 2
BALANCED_BRANCH_MIN_SAMPLE_RATIO = 0.15
TANK_TARGET_SUBTYPES = {
    "Dark Knight",
    "DarkKnight",
    "Gunbreaker",
    "Paladin",
    "Warrior",
}
SUPPORTED_CLASSIFICATIONS = {
    "raidwide",
    "tankbuster",
    "dual_tankbuster",
    "small_party",
}


def classify_ability_type(ability_type_code: Any) -> str:
    code = str(ability_type_code) if ability_type_code is not None else None
    if code == "128":
        return "physical"
    if code == "1024":
        return "magical"
    if code == "1":
        return "status_or_setup"
    if code == "8":
        return "buff_or_debuff"
    if code == "32":
        return "special"
    return "unknown"


def classify_hit_type(hit_type: Any, damage: dict[str, Any]) -> str:
    if hit_type is None:
        return "unknown"
    hit_type = int(hit_type)
    if hit_type == 1:
        return "landed"
    if hit_type == 20:
        return "blocked" if damage.get("blocked") else "landed"
    if hit_type == 10:
        return "zero_damage_or_immune"
    return "unknown"


def simplify_event(event: dict[str, Any]) -> dict[str, Any]:
    ability = event.get("ability") or {}
    damage = event.get("damage") or {}
    target = event.get("target") or {}

    return {
        "timestamp": event.get("timestamp"),
        "timestamp_ms": event.get("timestamp_ms"),
        "ability_name": ability.get("name"),
        "unmitigated_damage": damage.get("unmitigated_amount"),
        "ability_type": classify_ability_type(ability.get("type")),
        "hit_type": classify_hit_type(event.get("hit_type"), damage),
        "target_id": target.get("id"),
        "target_subtype": target.get("sub_type"),
        "target_name": target.get("name"),
        "is_dot": bool(event.get("tick")),
        "multiplier": damage.get("multiplier"),
    }


def build_postprocessed_fight(fight: dict[str, Any], fight_index: int) -> dict[str, Any]:
    damage_events = [simplify_event(event) for event in fight.get("events") or []]
    return {
        "fight_index": fight_index,
        "fight_id": fight.get("fight_id"),
        "fight_name": fight.get("name"),
        "party_size": len(fight.get("friendly_player_ids") or []),
        "damage_events": damage_events,
    }


def build_postprocessed_report(report_timeline: dict[str, Any]) -> dict[str, Any]:
    fights = [
        build_postprocessed_fight(fight, fight_index)
        for fight_index, fight in enumerate(report_timeline.get("fights") or [])
    ]
    return {
        "encounter": {"code": (report_timeline.get("encounter") or {}).get("code")},
        "report": {"code": (report_timeline.get("report") or {}).get("code")},
        "fights": fights,
    }


def compute_bucket_medians(postprocessed_reports: list[dict[str, Any]]) -> dict[int, int]:
    fight_buckets: dict[int, list[int]] = {}
    for report in postprocessed_reports:
        for fight in report.get("fights") or []:
            damage_events = fight.get("damage_events") or []
            if not damage_events:
                continue
            first_timestamp = damage_events[0].get("timestamp_ms")
            if first_timestamp is None:
                continue
            fight_buckets.setdefault(int(fight["fight_index"]), []).append(int(first_timestamp))

    return {
        fight_index: int(median(timestamps))
        for fight_index, timestamps in fight_buckets.items()
    }


def align_damage_event(event: dict[str, Any], offset_ms: int) -> dict[str, Any]:
    aligned_event = deepcopy(event)
    source_timestamp = aligned_event.get("timestamp_ms")
    if source_timestamp is None:
        return aligned_event

    aligned_timestamp_ms = int(source_timestamp) + int(offset_ms)
    aligned_event["timestamp_ms"] = aligned_timestamp_ms
    aligned_event["timestamp"] = format_timestamp(aligned_timestamp_ms)
    return aligned_event


def build_aligned_fight(fight: dict[str, Any], bucket_medians: dict[int, int]) -> dict[str, Any]:
    damage_events = fight.get("damage_events") or []
    source_first_event_ms = damage_events[0].get("timestamp_ms") if damage_events else None
    median_first_event_ms = bucket_medians.get(int(fight.get("fight_index", -1)))

    if not damage_events or source_first_event_ms is None or median_first_event_ms is None:
        aligned_events: list[dict[str, Any]] = []
    else:
        offset_ms = int(median_first_event_ms) - int(source_first_event_ms)
        aligned_events = [align_damage_event(event, offset_ms) for event in damage_events]

    return {
        "fight_index": fight.get("fight_index"),
        "fight_id": fight.get("fight_id"),
        "fight_name": fight.get("fight_name"),
        "party_size": fight.get("party_size"),
        "damage_events": aligned_events,
    }


def build_aligned_postprocessed_reports(postprocessed_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bucket_medians = compute_bucket_medians(postprocessed_reports)
    aligned_reports: list[dict[str, Any]] = []

    for report in postprocessed_reports:
        aligned_reports.append(
            {
                "encounter": deepcopy(report.get("encounter") or {}),
                "report": deepcopy(report.get("report") or {}),
                "fights": [
                    build_aligned_fight(fight, bucket_medians)
                    for fight in report.get("fights") or []
                ],
            }
        )

    return aligned_reports


def build_fight_windows(fight: dict[str, Any]) -> list[dict[str, Any]]:
    events = sorted(
        [
            event
            for event in (fight.get("damage_events") or [])
            if event.get("timestamp_ms") is not None and event.get("ability_name")
        ],
        key=lambda event: int(event["timestamp_ms"]),
    )
    if not events:
        return []

    party_size = _coerce_positive_int(fight.get("party_size"))
    non_dot_events = [event for event in events if not event.get("is_dot")]
    dot_events = [event for event in events if event.get("is_dot")]
    windows = build_non_dot_windows(non_dot_events, party_size=party_size)
    windows.extend(build_dot_windows(dot_events, party_size=party_size))
    windows.sort(key=lambda window: int(window["timestamp_ms"]))
    return windows


def build_window(
    events: list[dict[str, Any]],
    timestamp_ms: int,
    duration_ms: int | None = None,
    party_size: int | None = None,
) -> dict[str, Any]:
    return {
        "timestamp_ms": int(timestamp_ms),
        "ability_names": sorted(
            {
                str(event["ability_name"])
                for event in events
                if event.get("ability_name")
            }
        ),
        "events": [deepcopy(event) for event in events],
        "duration_ms": duration_ms,
        "party_size": party_size,
    }


def build_non_dot_windows(
    events: list[dict[str, Any]],
    *,
    party_size: int | None = None,
) -> list[dict[str, Any]]:
    if not events:
        return []

    windows: list[dict[str, Any]] = []
    current_events: list[dict[str, Any]] = []
    current_start_ms: int | None = None

    def flush_current_window() -> None:
        nonlocal current_events, current_start_ms
        if not current_events:
            return
        timestamps = [int(event["timestamp_ms"]) for event in current_events]
        windows.append(
            build_window(
                current_events,
                int(median(timestamps)),
                party_size=party_size,
            )
        )
        current_events = []
        current_start_ms = None

    for event in events:
        event_timestamp = int(event["timestamp_ms"])
        if current_start_ms is None:
            current_start_ms = event_timestamp
            current_events = [event]
            continue

        if event_timestamp - current_start_ms <= TIMELINE_MERGE_WINDOW_MS:
            current_events.append(event)
            continue

        flush_current_window()
        current_start_ms = event_timestamp
        current_events = [event]

    flush_current_window()
    return windows


def build_dot_windows(
    events: list[dict[str, Any]],
    *,
    party_size: int | None = None,
) -> list[dict[str, Any]]:
    events_by_key: dict[tuple[str | None, str | None, str | None], list[dict[str, Any]]] = {}
    for event in events:
        events_by_key.setdefault(
            (
                event.get("ability_name"),
                event.get("target_subtype"),
                event.get("target_name"),
            ),
            [],
        ).append(event)

    windows: list[dict[str, Any]] = []
    for grouped_events in events_by_key.values():
        grouped_events.sort(key=lambda event: int(event["timestamp_ms"]))
        current_run: list[dict[str, Any]] = []
        previous_timestamp_ms: int | None = None

        def flush_run() -> None:
            nonlocal current_run, previous_timestamp_ms
            if not current_run:
                return
            start_timestamp = int(current_run[0]["timestamp_ms"])
            end_timestamp = int(current_run[-1]["timestamp_ms"])
            windows.append(
                build_window(
                    current_run,
                    timestamp_ms=start_timestamp,
                    duration_ms=max(end_timestamp - start_timestamp, 0),
                    party_size=party_size,
                )
            )
            current_run = []
            previous_timestamp_ms = None

        for event in grouped_events:
            event_timestamp_ms = int(event["timestamp_ms"])
            if previous_timestamp_ms is None:
                current_run = [event]
                previous_timestamp_ms = event_timestamp_ms
                continue

            if event_timestamp_ms - previous_timestamp_ms <= DOT_GAP_TOLERANCE_MS:
                current_run.append(event)
                previous_timestamp_ms = event_timestamp_ms
                continue

            flush_run()
            current_run = [event]
            previous_timestamp_ms = event_timestamp_ms

        flush_run()

    return windows


def windows_overlap(reference_window: dict[str, Any], candidate_window: dict[str, Any]) -> bool:
    return bool(
        set(reference_window.get("ability_names") or [])
        & set(candidate_window.get("ability_names") or [])
    )


def compute_lcs_pairs(
    reference_windows: list[dict[str, Any]],
    candidate_windows: list[dict[str, Any]],
) -> list[tuple[int, int]]:
    reference_count = len(reference_windows)
    candidate_count = len(candidate_windows)
    dp = [[0] * (candidate_count + 1) for _ in range(reference_count + 1)]

    for reference_index in range(reference_count):
        for candidate_index in range(candidate_count):
            if windows_overlap(
                reference_windows[reference_index],
                candidate_windows[candidate_index],
            ):
                dp[reference_index + 1][candidate_index + 1] = (
                    dp[reference_index][candidate_index] + 1
                )
            else:
                dp[reference_index + 1][candidate_index + 1] = max(
                    dp[reference_index][candidate_index + 1],
                    dp[reference_index + 1][candidate_index],
                )

    matches: list[tuple[int, int]] = []
    reference_index = reference_count
    candidate_index = candidate_count
    while reference_index > 0 and candidate_index > 0:
        if windows_overlap(
            reference_windows[reference_index - 1],
            candidate_windows[candidate_index - 1],
        ) and dp[reference_index][candidate_index] == dp[reference_index - 1][candidate_index - 1] + 1:
            matches.append((reference_index - 1, candidate_index - 1))
            reference_index -= 1
            candidate_index -= 1
        elif dp[reference_index - 1][candidate_index] >= dp[reference_index][candidate_index - 1]:
            reference_index -= 1
        else:
            candidate_index -= 1

    matches.reverse()
    return matches


def get_row_windows(row: dict[str, Any]) -> list[dict[str, Any]]:
    cached_windows = row.get("windows")
    if cached_windows is not None:
        return cached_windows
    windows = build_fight_windows(row["fight"])
    row["windows"] = windows
    return windows


def split_unmatched_reference_ranges(
    reference_windows: list[dict[str, Any]],
    candidate_windows: list[dict[str, Any]],
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    if not reference_windows or not candidate_windows:
        return [], []

    matched_pairs = compute_lcs_pairs(reference_windows, candidate_windows)
    matched_reference_indices = [reference_index for reference_index, _ in matched_pairs]
    matched_reference_set = set(matched_reference_indices)
    unmatched_indices = [
        reference_index
        for reference_index in range(len(reference_windows))
        if reference_index not in matched_reference_set
    ]
    if not unmatched_indices:
        return [], []

    contiguous_ranges: list[tuple[int, int]] = []
    range_start = unmatched_indices[0]
    range_end = unmatched_indices[0]
    for unmatched_index in unmatched_indices[1:]:
        if unmatched_index == range_end + 1:
            range_end = unmatched_index
            continue
        contiguous_ranges.append((range_start, range_end))
        range_start = unmatched_index
        range_end = unmatched_index
    contiguous_ranges.append((range_start, range_end))

    if not matched_reference_indices:
        return contiguous_ranges, []

    last_matched_reference_index = max(matched_reference_indices)
    structural_ranges: list[tuple[int, int]] = []
    trailing_ranges: list[tuple[int, int]] = []
    for range_start, range_end in contiguous_ranges:
        if range_start > last_matched_reference_index:
            trailing_ranges.append((range_start, range_end))
        else:
            structural_ranges.append((range_start, range_end))
    return structural_ranges, trailing_ranges


def build_branch_signature(
    reference_windows: list[dict[str, Any]],
    candidate_windows: list[dict[str, Any]],
) -> tuple[tuple[int, int], ...]:
    if not reference_windows or not candidate_windows:
        return ()

    contiguous_ranges, _ = split_unmatched_reference_ranges(reference_windows, candidate_windows)
    if not contiguous_ranges:
        return ()

    significant_ranges: list[tuple[int, int]] = []
    for range_start, range_end in contiguous_ranges:
        if is_significant_reference_range(reference_windows, range_start, range_end):
            significant_ranges.append((range_start, range_end))

    return tuple(significant_ranges)


def range_window_count(ranges: tuple[tuple[int, int], ...] | list[tuple[int, int]]) -> int:
    return sum((range_end - range_start + 1) for range_start, range_end in ranges)


def largest_significant_range_fraction(
    reference_windows: list[dict[str, Any]],
    candidate_windows: list[dict[str, Any]],
) -> float:
    if not reference_windows:
        return 1.0
    significant_ranges = build_branch_signature(reference_windows, candidate_windows)
    if not significant_ranges:
        return 0.0
    largest_range = max(range_end - range_start + 1 for range_start, range_end in significant_ranges)
    return largest_range / len(reference_windows)


def significant_range_fraction(
    reference_windows: list[dict[str, Any]],
    candidate_windows: list[dict[str, Any]],
) -> float:
    if not reference_windows:
        return 1.0
    significant_ranges = build_branch_signature(reference_windows, candidate_windows)
    if not significant_ranges:
        return 0.0
    return range_window_count(significant_ranges) / len(reference_windows)


def build_row_route_comparison(
    left_row: dict[str, Any],
    right_row: dict[str, Any],
    comparison_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cache_key = (id(left_row), id(right_row))
    if comparison_cache is not None and cache_key in comparison_cache:
        return comparison_cache[cache_key]

    left_windows = get_row_windows(left_row)
    right_windows = get_row_windows(right_row)
    lcs_pairs = compute_lcs_pairs(left_windows, right_windows) if left_windows and right_windows else []
    lcs_count = len(lcs_pairs)
    min_window_count = min(len(left_windows), len(right_windows)) if left_windows and right_windows else 0
    max_window_count = max(len(left_windows), len(right_windows)) if left_windows or right_windows else 0

    left_significant_ranges = build_branch_signature(left_windows, right_windows)
    right_significant_ranges = build_branch_signature(right_windows, left_windows)
    left_significant_fraction = (
        range_window_count(left_significant_ranges) / len(left_windows)
        if left_windows and left_significant_ranges
        else 0.0
    )
    right_significant_fraction = (
        range_window_count(right_significant_ranges) / len(right_windows)
        if right_windows and right_significant_ranges
        else 0.0
    )
    left_largest_significant_fraction = (
        max(range_end - range_start + 1 for range_start, range_end in left_significant_ranges) / len(left_windows)
        if left_windows and left_significant_ranges
        else 0.0
    )
    right_largest_significant_fraction = (
        max(range_end - range_start + 1 for range_start, range_end in right_significant_ranges) / len(right_windows)
        if right_windows and right_significant_ranges
        else 0.0
    )

    comparison = {
        "left_windows": left_windows,
        "right_windows": right_windows,
        "lcs_count": lcs_count,
        "ratio_min": (lcs_count / min_window_count) if min_window_count else 0.0,
        "ratio_max": (lcs_count / max_window_count) if max_window_count else 0.0,
        "left_significant_ranges": left_significant_ranges,
        "right_significant_ranges": right_significant_ranges,
        "left_significant_fraction": left_significant_fraction,
        "right_significant_fraction": right_significant_fraction,
        "left_largest_significant_fraction": left_largest_significant_fraction,
        "right_largest_significant_fraction": right_largest_significant_fraction,
    }
    if comparison_cache is not None:
        comparison_cache[cache_key] = comparison
    return comparison


def rows_share_route_family(
    left_row: dict[str, Any],
    right_row: dict[str, Any],
    comparison_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
) -> bool:
    comparison = build_row_route_comparison(left_row, right_row, comparison_cache)
    if comparison["lcs_count"] == 0 or comparison["ratio_min"] < BRANCH_MERGE_MIN_RATIO_MIN:
        return False

    if comparison["ratio_max"] < BRANCH_MERGE_MIN_RATIO_MAX:
        left_windows = comparison["left_windows"]
        right_windows = comparison["right_windows"]
        if len(left_windows) >= len(right_windows):
            return (
                comparison["ratio_min"] >= CONTAINED_ROUTE_MIN_RATIO_MIN
                and not comparison["right_significant_ranges"]
                and comparison["left_significant_fraction"]
                <= CONTAINED_ROUTE_MAX_SIGNIFICANT_RANGE_FRACTION
            )
        return (
            comparison["ratio_min"] >= CONTAINED_ROUTE_MIN_RATIO_MIN
            and not comparison["left_significant_ranges"]
            and comparison["right_significant_fraction"]
            <= CONTAINED_ROUTE_MAX_SIGNIFICANT_RANGE_FRACTION
        )

    return (
        comparison["left_largest_significant_fraction"]
        <= BRANCH_MERGE_MAX_SIGNIFICANT_RANGE_FRACTION
        and comparison["right_largest_significant_fraction"]
        <= BRANCH_MERGE_MAX_SIGNIFICANT_RANGE_FRACTION
    )


def cluster_pair_total_lcs_score(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    comparison_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
) -> int:
    return sum(
        build_row_route_comparison(left_row, right_row, comparison_cache)["lcs_count"]
        for left_row in left_rows
        for right_row in right_rows
    )


def cluster_rows_share_route_family(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    comparison_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
) -> bool:
    return all(
        rows_share_route_family(left_row, right_row, comparison_cache)
        for left_row in left_rows
        for right_row in right_rows
    )


def is_significant_reference_range(
    reference_windows: list[dict[str, Any]],
    range_start: int,
    range_end: int,
) -> bool:
    range_length = range_end - range_start + 1
    range_duration = (
        int(reference_windows[range_end]["timestamp_ms"])
        - int(reference_windows[range_start]["timestamp_ms"])
    )
    return (
        range_length >= MIN_STRUCTURAL_SKIP_EVENTS
        and range_duration >= MIN_STRUCTURAL_SKIP_DURATION_MS
    )


def find_significant_tail_start_timestamp(branch_rows: list[dict[str, Any]]) -> int | None:
    longest_branch_row = choose_longest_branch_row(branch_rows)
    if longest_branch_row is None:
        return None

    longest_windows = get_row_windows(longest_branch_row)
    significant_tail_starts: list[int] = []
    for row in branch_rows:
        if row is longest_branch_row:
            continue
        _, trailing_ranges = split_unmatched_reference_ranges(longest_windows, get_row_windows(row))
        for range_start, range_end in trailing_ranges:
            if is_significant_reference_range(longest_windows, range_start, range_end):
                significant_tail_starts.append(
                    int(longest_windows[range_start]["timestamp_ms"])
                )

    if not significant_tail_starts:
        return None
    return min(significant_tail_starts)


def build_time_clusters(branch_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    for row in branch_rows:
        report_code = row["report_code"]
        for window in get_row_windows(row):
            windows.append(
                {
                    "report_code": report_code,
                    "timestamp_ms": int(window["timestamp_ms"]),
                    "ability_names": list(window["ability_names"]),
                    "events": [deepcopy(event) for event in window.get("events") or []],
                    "duration_ms": window.get("duration_ms"),
                    "party_size": window.get("party_size"),
                }
            )

    windows.sort(key=lambda window: window["timestamp_ms"])
    if not windows:
        return []

    clusters: list[dict[str, Any]] = []
    current_cluster: dict[str, Any] | None = None

    def flush_cluster() -> None:
        nonlocal current_cluster
        if current_cluster is not None:
            clusters.append(current_cluster)
            current_cluster = None

    for window in windows:
        if current_cluster is None:
            current_cluster = {
                "start_ms": window["timestamp_ms"],
                "windows": [window],
            }
            continue

        if window["timestamp_ms"] - int(current_cluster["start_ms"]) <= TIMELINE_MERGE_WINDOW_MS:
            current_cluster["windows"].append(window)
            continue

        flush_cluster()
        current_cluster = {
            "start_ms": window["timestamp_ms"],
            "windows": [window],
        }

    flush_cluster()
    return clusters


def collect_cluster_events(cluster: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        deepcopy(event)
        for window in cluster.get("windows") or []
        for event in window.get("events") or []
    ]


def collect_cluster_windows(cluster: dict[str, Any]) -> list[dict[str, Any]]:
    return [deepcopy(window) for window in cluster.get("windows") or []]


def normalize_sort_value(value: Any) -> tuple[int, Any]:
    if value is None:
        return (0, "")
    if isinstance(value, bool):
        return (1, int(value))
    if isinstance(value, (int, float)):
        return (2, value)
    return (3, str(value))


def collect_unique_field_values(events: list[dict[str, Any]], field_name: str) -> list[Any]:
    values = {
        event.get(field_name)
        for event in events
        if field_name in event and event.get(field_name) is not None
    }
    return sorted(values, key=normalize_sort_value)


def add_cluster_field(event: dict[str, Any], cluster_events: list[dict[str, Any]], field_name: str) -> None:
    values = collect_unique_field_values(cluster_events, field_name)
    if not values:
        event[field_name] = None
        return
    if len(values) == 1:
        event[field_name] = values[0]
        return
    event[field_name] = values


def normalize_damage_sample(event: dict[str, Any]) -> float | None:
    damage = event.get("unmitigated_damage")
    multiplier = event.get("multiplier")
    if not isinstance(damage, (int, float)) or damage <= 0:
        return None
    if isinstance(multiplier, (int, float)) and multiplier > 0:
        return float(damage) / float(multiplier)
    return float(damage)


def summarize_representative_damage(
    occurrences: list[dict[str, Any]],
) -> int | None:
    if not occurrences:
        return None

    normalized_samples: list[float] = []
    for occurrence in occurrences:
        normalized_samples.extend(
            sample
            for sample in (
                normalize_damage_sample(event)
                for event in (occurrence.get("events") or [])
            )
            if sample is not None
        )

    if not normalized_samples:
        return None
    return int(round(float(median(normalized_samples))))


def summarize_duration_ms(windows: list[dict[str, Any]]) -> int | None:
    durations = [
        int(window["duration_ms"])
        for window in windows
        if isinstance(window.get("duration_ms"), (int, float))
    ]
    if not durations:
        return None
    return int(median(durations))


def summarize_occurrence_duration_ms(occurrences: list[dict[str, Any]]) -> int | None:
    durations: list[int] = []
    for occurrence in occurrences:
        duration = occurrence.get("duration_ms")
        if isinstance(duration, (int, float)):
            durations.append(int(duration))
    if not durations:
        return None
    return int(median(durations))


def is_tank_target_subtype(target_subtype: Any) -> bool:
    return str(target_subtype) in TANK_TARGET_SUBTYPES


def build_target_key(event: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (
        event.get("target_id"),
        event.get("target_name"),
        event.get("target_subtype"),
    )


def build_unique_targets(events: list[dict[str, Any]]) -> set[tuple[Any, Any, Any]]:
    return {
        build_target_key(event)
        for event in events
        if any(value is not None for value in build_target_key(event))
    }


def raidwide_min_target_count(party_size: int | None) -> int:
    if party_size is None or party_size <= 0:
        return 5
    threshold = ceil(party_size * 0.75)
    if party_size >= 6:
        # Allow one missing player in observed logs to tolerate deaths or invulns
        # while still requiring a clearly party-wide hit profile.
        threshold = max(threshold - 1, 5 if party_size >= 8 else 4)
    return max(threshold, 1)


def classify_mechanic_profile(
    events: list[dict[str, Any]],
    party_size: int | None,
) -> str | None:
    if not events:
        return None
    unique_targets = build_unique_targets(events)
    if not unique_targets:
        return None

    target_count = len(unique_targets)
    all_tanks = all(
        is_tank_target_subtype(target_subtype)
        for _, _, target_subtype in unique_targets
    )
    if target_count == 1 and all_tanks:
        return "tankbuster"
    if target_count == 2 and all_tanks:
        return "dual_tankbuster"
    if target_count == 4:
        return "small_party"
    if target_count >= raidwide_min_target_count(party_size):
        return "raidwide"
    return None


def summarize_classification_for_ability(
    occurrences: list[dict[str, Any]],
) -> str | None:
    profile_counts: Counter[str] = Counter()

    for occurrence in occurrences:
        ability_events = [deepcopy(event) for event in occurrence.get("events") or []]
        if not ability_events:
            continue
        profile = classify_mechanic_profile(
            ability_events,
            _coerce_positive_int(occurrence.get("party_size")),
        )
        if profile is not None:
            profile_counts[profile] += 1

    if not profile_counts:
        return None

    most_common = profile_counts.most_common()
    if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
        return None
    return most_common[0][0]


def summarize_is_dot_for_ability(
    occurrences: list[dict[str, Any]],
) -> bool | None:
    ability_events = [
        deepcopy(event)
        for occurrence in occurrences
        for event in occurrence.get("events") or []
    ]
    if not ability_events:
        return None
    return any(bool(event.get("is_dot")) for event in ability_events)


def summarize_is_multi_hit_for_ability(
    occurrences: list[dict[str, Any]],
) -> bool | None:
    if not occurrences:
        return None

    for occurrence in occurrences:
        non_dot_events = [
            deepcopy(event)
            for event in occurrence.get("events") or []
            if not event.get("is_dot")
        ]
        if not non_dot_events:
            continue
        if len(non_dot_events) > len(build_unique_targets(non_dot_events)):
            return True
    return False


def has_combined_abilities(
    cluster_windows: list[dict[str, Any]],
    supported_ability_names: set[str],
) -> bool:
    return any(
        len(
            [
                ability_name
                for ability_name in (window.get("ability_names") or [])
                if ability_name in supported_ability_names
            ]
        ) > 1
        for window in cluster_windows
    )


def summarize_field_for_ability(
    windows: list[dict[str, Any]],
    ability_name: str,
    field_name: str,
) -> Any:
    relevant_windows = [
        deepcopy(window)
        for window in windows
        if ability_name in (window.get("ability_names") or [])
    ]
    ability_events = [
        deepcopy(event)
        for window in relevant_windows
        for event in window.get("events") or []
        if event.get("ability_name") == ability_name
    ]
    occurrences = build_ability_occurrences(relevant_windows, ability_name)
    if field_name == "unmitigated_damage":
        return summarize_representative_damage(occurrences)
    if field_name == "classification":
        return summarize_classification_for_ability(occurrences)
    if field_name == "is_dot":
        return summarize_is_dot_for_ability(occurrences)
    if field_name == "is_multi_hit":
        return summarize_is_multi_hit_for_ability(occurrences)
    if field_name == "duration_ms":
        return summarize_occurrence_duration_ms(occurrences)

    values = collect_unique_field_values(ability_events, field_name)
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return values


def add_ability_summary_field(
    event: dict[str, Any],
    ability_summaries: dict[str, dict[str, Any]],
    ability_names: list[str],
    field_name: str,
) -> None:
    field_values = [
        ability_summaries[ability_name].get(field_name)
        for ability_name in ability_names
    ]
    if not any(value is not None for value in field_values):
        return
    if len(ability_names) <= 1:
        event[field_name] = field_values[0]
        return
    event[field_name] = field_values


def build_generated_timeline_event(cluster: dict[str, Any], branch_size: int) -> dict[str, Any] | None:
    return build_generated_timeline_event_for_threshold(cluster, branch_size, TIMELINE_STABILITY_THRESHOLD)


def build_generated_timeline_event_for_threshold(
    cluster: dict[str, Any],
    branch_size: int,
    minimum_presence_ratio: float,
) -> dict[str, Any] | None:
    report_codes = {
        window["report_code"]
        for window in cluster.get("windows") or []
    }
    if branch_size == 0:
        return None
    if len(report_codes) / branch_size < minimum_presence_ratio:
        return None

    cluster_windows = collect_cluster_windows(cluster)
    all_ability_names = sorted(
        {
            ability_name
            for window in cluster.get("windows") or []
            for ability_name in window.get("ability_names") or []
        }
    )
    ability_summaries = {
        ability_name: {
            field_name: summarize_field_for_ability(cluster_windows, ability_name, field_name)
            for field_name in (
                "unmitigated_damage",
                "ability_type",
                "is_dot",
                "is_multi_hit",
                "classification",
                "duration_ms",
            )
        }
        for ability_name in all_ability_names
    }
    ability_names = [
        ability_name
        for ability_name in all_ability_names
        if ability_summaries[ability_name].get("classification") in SUPPORTED_CLASSIFICATIONS
    ]
    if not ability_names:
        return None

    timestamp_ms = int(
        median([int(window["timestamp_ms"]) for window in cluster.get("windows") or []])
    )

    event: dict[str, Any] = {
        "timestamp": format_timestamp(timestamp_ms),
        "timestamp_ms": timestamp_ms,
    }
    if len(ability_names) <= 1:
        event["event_kind"] = "stable"
        event["ability_name"] = ability_names[0] if ability_names else None
    elif has_combined_abilities(cluster_windows, set(ability_names)):
        event["event_kind"] = "combined"
        event["ability_names"] = ability_names
    else:
        event["event_kind"] = "variable"
        event["ability_names"] = ability_names

    for field_name in (
        "unmitigated_damage",
        "ability_type",
        "is_dot",
        "is_multi_hit",
        "classification",
        "duration_ms",
    ):
        add_ability_summary_field(event, ability_summaries, ability_names, field_name)
    return event


def _coerce_positive_int(value: Any) -> int | None:
    if not isinstance(value, (int, float)):
        return None
    integer = int(value)
    if integer <= 0:
        return None
    return integer


def build_ability_occurrences(
    windows: list[dict[str, Any]],
    ability_name: str,
) -> list[dict[str, Any]]:
    if not windows:
        return []

    grouped_occurrences: dict[str, dict[str, Any]] = {}
    anonymous_index = 0

    for window in windows:
        if ability_name not in (window.get("ability_names") or []):
            continue
        report_code = window.get("report_code")
        if report_code is None:
            report_code = f"__anonymous_{anonymous_index}"
            anonymous_index += 1

        occurrence = grouped_occurrences.setdefault(
            str(report_code),
            {
                "events": [],
                "duration_samples": [],
                "party_size": window.get("party_size"),
            },
        )
        occurrence["events"].extend(
            deepcopy(event)
            for event in window.get("events") or []
            if event.get("ability_name") == ability_name
        )
        if isinstance(window.get("duration_ms"), (int, float)):
            occurrence["duration_samples"].append(int(window["duration_ms"]))
        if occurrence.get("party_size") is None:
            occurrence["party_size"] = window.get("party_size")

    occurrences: list[dict[str, Any]] = []
    for occurrence in grouped_occurrences.values():
        duration_samples = occurrence.pop("duration_samples")
        occurrence["duration_ms"] = (
            int(median(duration_samples))
            if duration_samples
            else None
        )
        occurrences.append(occurrence)
    return occurrences


def choose_longest_branch_row(branch_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not branch_rows:
        return None

    def sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
        windows = get_row_windows(row)
        last_timestamp = int(windows[-1]["timestamp_ms"]) if windows else -1
        return (len(windows), last_timestamp, str(row.get("report_code") or ""))

    return max(branch_rows, key=sort_key)


def get_row_last_timestamp_ms(row: dict[str, Any]) -> int:
    windows = get_row_windows(row)
    if not windows:
        return -1
    return int(windows[-1]["timestamp_ms"])


def choose_representative_branch_row(
    branch_rows: list[dict[str, Any]],
    comparison_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if not branch_rows:
        return None

    def sort_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
        total_lcs_score = sum(
            build_row_route_comparison(row, other_row, comparison_cache)["lcs_count"]
            for other_row in branch_rows
            if other_row is not row
        )
        windows = get_row_windows(row)
        last_timestamp = int(windows[-1]["timestamp_ms"]) if windows else -1
        return (
            -total_lcs_score,
            -len(windows),
            -last_timestamp,
            str(row.get("report_code") or ""),
        )

    return min(branch_rows, key=sort_key)


def get_branch_report_codes(branch_rows: list[dict[str, Any]]) -> list[str]:
    return sorted(str(row.get("report_code") or "") for row in branch_rows)


def cluster_sort_key(
    branch_rows: list[dict[str, Any]],
    comparison_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
) -> tuple[int, int, int, list[str]]:
    representative = choose_representative_branch_row(branch_rows, comparison_cache)
    representative_length = len(get_row_windows(representative)) if representative else 0
    representative_last_timestamp = get_row_last_timestamp_ms(representative) if representative else -1
    return (
        -len(branch_rows),
        -representative_length,
        -representative_last_timestamp,
        get_branch_report_codes(branch_rows),
    )


def cluster_merge_sort_key(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    comparison_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
) -> tuple[int, int, list[str], list[str]]:
    return (
        -(len(left_rows) + len(right_rows)),
        -cluster_pair_total_lcs_score(left_rows, right_rows, comparison_cache),
        get_branch_report_codes(left_rows),
        get_branch_report_codes(right_rows),
    )


def cluster_rows_by_route_family(
    fight_rows: list[dict[str, Any]],
    comparison_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
) -> list[list[dict[str, Any]]]:
    clusters = [[row] for row in fight_rows]

    while True:
        best_pair: tuple[int, int] | None = None
        best_pair_key: tuple[int, int, list[str], list[str]] | None = None

        for left_index in range(len(clusters)):
            for right_index in range(left_index + 1, len(clusters)):
                left_rows = clusters[left_index]
                right_rows = clusters[right_index]
                if not cluster_rows_share_route_family(left_rows, right_rows, comparison_cache):
                    continue

                candidate_key = cluster_merge_sort_key(left_rows, right_rows, comparison_cache)
                if best_pair_key is None or candidate_key < best_pair_key:
                    best_pair = (left_index, right_index)
                    best_pair_key = candidate_key

        if best_pair is None:
            break

        left_index, right_index = best_pair
        merged_rows = clusters[left_index] + clusters[right_index]
        clusters[left_index] = merged_rows
        clusters.pop(right_index)

    return clusters


def collect_significant_range_start_timestamps(
    reference_windows: list[dict[str, Any]],
    significant_ranges: tuple[tuple[int, int], ...] | list[tuple[int, int]],
) -> list[int]:
    return [
        int(reference_windows[range_start]["timestamp_ms"])
        for range_start, _ in significant_ranges
    ]


def find_first_divergence_timestamp_ms(
    primary_row: dict[str, Any] | None,
    branch_row: dict[str, Any] | None,
    comparison_cache: dict[tuple[int, int], dict[str, Any]] | None = None,
) -> int | None:
    if primary_row is None or branch_row is None:
        return None

    comparison = build_row_route_comparison(primary_row, branch_row, comparison_cache)
    divergence_timestamps = collect_significant_range_start_timestamps(
        comparison["left_windows"],
        comparison["left_significant_ranges"],
    )
    divergence_timestamps.extend(
        collect_significant_range_start_timestamps(
            comparison["right_windows"],
            comparison["right_significant_ranges"],
        )
    )
    if not divergence_timestamps:
        return None
    return min(divergence_timestamps)


def build_generated_timeline(
    encounter_code: str,
    fight_index: int,
    branch_index: int,
    branch_rows: list[dict[str, Any]],
    *,
    tail_reference_rows: list[dict[str, Any]] | None = None,
    presence_branch_size: int | None = None,
    sample_count: int | None = None,
    sample_ratio: float | None = None,
    report_codes: list[str] | None = None,
    is_primary_branch: bool = False,
    first_divergence_timestamp_ms: int | None = None,
) -> dict[str, Any]:
    clusters = build_time_clusters(branch_rows)
    effective_branch_size = presence_branch_size or len(branch_rows)
    standard_events_by_cluster_index: dict[int, dict[str, Any]] = {}
    for cluster_index, cluster in enumerate(clusters):
        event = build_generated_timeline_event(cluster, effective_branch_size)
        if event is not None:
            standard_events_by_cluster_index[cluster_index] = event

    tail_rows = tail_reference_rows or branch_rows
    longest_branch_row = choose_longest_branch_row(tail_rows)
    longest_report_code = longest_branch_row["report_code"] if longest_branch_row else None
    significant_tail_start_timestamp = find_significant_tail_start_timestamp(tail_rows)
    last_standard_cluster_index = max(standard_events_by_cluster_index, default=-1)

    events: list[dict[str, Any]] = []
    for cluster_index, cluster in enumerate(clusters):
        standard_event = standard_events_by_cluster_index.get(cluster_index)
        if standard_event is not None:
            events.append(standard_event)
            continue
        if (
            cluster_index > last_standard_cluster_index
            and longest_report_code is not None
            and significant_tail_start_timestamp is not None
            and any(
                window["report_code"] == longest_report_code
                for window in cluster.get("windows") or []
            )
        ):
            tail_event = build_generated_timeline_event_for_threshold(
                cluster,
                len(branch_rows),
                minimum_presence_ratio=0.0,
            )
            if tail_event is not None:
                events.append(tail_event)

    return {
        "encounter_code": encounter_code,
        "fight_index": fight_index,
        "branch_index": branch_index,
        "sample_count": len(branch_rows) if sample_count is None else sample_count,
        "sample_ratio": (
            round((len(branch_rows) / effective_branch_size) if effective_branch_size else 0.0, 4)
            if sample_ratio is None
            else round(sample_ratio, 4)
        ),
        "report_codes": get_branch_report_codes(branch_rows) if report_codes is None else report_codes,
        "is_primary_branch": is_primary_branch,
        "first_divergence_timestamp_ms": first_divergence_timestamp_ms,
        "first_divergence_timestamp": (
            format_timestamp(first_divergence_timestamp_ms)
            if first_divergence_timestamp_ms is not None
            else None
        ),
        "events": events,
    }


def build_generated_timelines(aligned_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fight_rows_by_index: dict[int, list[dict[str, Any]]] = {}
    encounter_code = ""

    for report in aligned_reports:
        encounter_code = encounter_code or str((report.get("encounter") or {}).get("code") or "")
        report_code = str((report.get("report") or {}).get("code") or "")
        for fight in report.get("fights") or []:
            if not (fight.get("damage_events") or []):
                continue
            windows = build_fight_windows(fight)
            fight_rows_by_index.setdefault(int(fight["fight_index"]), []).append(
                {
                    "report_code": report_code,
                    "fight": fight,
                    "windows": windows,
                }
            )

    generated_timelines: list[dict[str, Any]] = []
    comparison_cache: dict[tuple[int, int], dict[str, Any]] = {}
    for fight_index in sorted(fight_rows_by_index):
        fight_rows = fight_rows_by_index[fight_index]
        route_clusters = cluster_rows_by_route_family(fight_rows, comparison_cache)
        route_clusters.sort(key=lambda rows: cluster_sort_key(rows, comparison_cache))
        if not route_clusters:
            continue

        total_samples = len(fight_rows)
        primary_core_rows = list(route_clusters[0])
        primary_branch_rows = list(primary_core_rows)
        primary_representative = choose_representative_branch_row(primary_core_rows, comparison_cache)
        retained_branches: list[dict[str, Any]] = [
            {
                "core_rows": primary_core_rows,
                "branch_rows": primary_branch_rows,
                "representative": primary_representative,
                "is_primary_branch": True,
                "first_divergence_timestamp_ms": None,
            }
        ]

        for route_cluster in route_clusters[1:]:
            representative = choose_representative_branch_row(route_cluster, comparison_cache)
            first_divergence_timestamp_ms = find_first_divergence_timestamp_ms(
                primary_representative,
                representative,
                comparison_cache,
            )
            sample_count = len(route_cluster)
            sample_ratio = sample_count / total_samples if total_samples else 0.0
            should_retain = (
                first_divergence_timestamp_ms is not None
                and (
                    sample_count >= BALANCED_BRANCH_MIN_REPORTS
                    or sample_ratio >= BALANCED_BRANCH_MIN_SAMPLE_RATIO
                )
            )
            if should_retain:
                retained_branches.append(
                    {
                        "core_rows": list(route_cluster),
                        "branch_rows": list(route_cluster),
                        "representative": representative,
                        "is_primary_branch": False,
                        "first_divergence_timestamp_ms": first_divergence_timestamp_ms,
                    }
                )
                continue

            primary_branch_rows.extend(route_cluster)

        for branch_index, branch_info in enumerate(retained_branches):
            branch_rows = branch_info["branch_rows"]
            generated_timelines.append(
                build_generated_timeline(
                    encounter_code=encounter_code,
                    fight_index=fight_index,
                    branch_index=branch_index,
                    branch_rows=branch_rows,
                    tail_reference_rows=branch_info["core_rows"],
                    presence_branch_size=len(branch_info["core_rows"]),
                    sample_count=len(branch_rows),
                    sample_ratio=(len(branch_rows) / total_samples) if total_samples else 0.0,
                    report_codes=get_branch_report_codes(branch_rows),
                    is_primary_branch=bool(branch_info["is_primary_branch"]),
                    first_divergence_timestamp_ms=branch_info["first_divergence_timestamp_ms"],
                )
            )

    return generated_timelines
