"""LangGraph pipeline for FFXIV timeline generation.

Pipeline steps:
1. fetch_cactbot  — Fetches cactbot timeline data from GitHub
2. fetch_guides   — Uses the LLM-driven GuideAgent to find & extract guides
3. synthesize     — LLM synthesizes a structured timeline from both sources
4. export         — Generates cactbot-compatible export text
"""

import logging
import time
from datetime import datetime
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from xiv_timeline.cactbot_client import CactbotClient
from xiv_timeline.guide_scraper import GuideAgent
from xiv_timeline.llm import get_llm
from xiv_timeline.synthesizer import TimelineSynthesizer

logger = logging.getLogger("xiv_timeline.graph")


# ---------------------------------------------------------------------------
# Pydantic output models — simplified timeline schema
# ---------------------------------------------------------------------------


class TimelineEntry(BaseModel):
    """A single boss ability in the timeline."""

    timestamp: float
    ability_name: str
    description: str | None = None
    unmitigated_damage: float | None = None
    ability_type: str | None = None
    is_dot: bool | None = None
    # Mitigation planning fields
    damage_min: float | None = None
    damage_max: float | None = None
    damage_median: float | None = None
    target_count: float | None = None
    # Multi-hit grouping fields
    hit_count: int = 1
    hits_per_cast: float | None = None
    time_range_start: float | None = None
    time_range_end: float | None = None


class TimelinePhase(BaseModel):
    """A phase in the boss encounter."""

    name: str
    start_time: float
    end_time: float
    entries: list[TimelineEntry]
    tips: list[str]


class SynthesizedTimeline(BaseModel):
    """Complete synthesized timeline for a boss."""

    boss_name: str
    expansion: str
    difficulty: str
    phases: list[TimelinePhase]
    notes: list[str]
    confidence: float
    generated_at: str


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------


import operator
from typing import Annotated, Any, TypedDict

def merge_dicts(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Merge two dictionaries."""
    if not a:
        return b
    if not b:
        return a
    res = a.copy()
    res.update(b)
    return res

def replace_list(a: list[Any], b: list[Any]) -> list[Any]:
    """Replace list a with list b (last write wins)."""
    return b if b else a

class TimelineState(TypedDict, total=False):
    """Shared state flowing through the LangGraph pipeline."""

    # Inputs
    boss_name: str
    expansion: str | None
    encounter_type: str | None
    difficulty: str | None

    # Intermediate data
    cactbot_data: Annotated[dict[str, Any], merge_dicts]
    guide_data: Annotated[dict[str, Any], merge_dicts]
    damage_data: Annotated[dict[str, Any], merge_dicts]

    # Outputs
    synthesized: Annotated[dict[str, Any], merge_dicts]
    fflogs_reference: Annotated[list[dict[str, Any]], replace_list]
    cactbot_export: str
    cactbot_raw: str


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert FFXIV raid timeline generator. Synthesize accurate boss
timelines by combining cactbot data (community timeline repository) with
strategy guide content.

Rules:
- Use cactbot timestamps as the source of truth for timing (every entry must have a timestamp from cactbot).
- Only include boss actions that have damage data from FFLogs. Do NOT include abilities with no damage values.
- Use guide content for phase context, detailed mechanic descriptions, and tips.
- Identify phase boundaries and group abilities into phases.
- Write concise, actionable tips for each phase.
- Provide detailed and helpful descriptions for the boss actions in `description` using the mechanics information.
- The `--sync--` action helps signify phase boundaries, but you should NEVER output `--sync--` in the actual timeline output entries.
- Set confidence based on how much data was available.
- When damage data is available, prioritize describing high-damage abilities and note mitigation requirements.
- Do NOT add numbered suffixes to ability names (e.g., do NOT write "Flame Floater 1", "Flame Floater 2"). Always use the base ability name exactly as it appears in the cactbot data. If the same ability appears multiple times in quick succession, list each occurrence separately with its own timestamp — post-processing will consolidate them.

Output a SynthesizedTimeline JSON object."""


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


async def fetch_damage_node(state: TimelineState) -> dict[str, Any]:
    """Fetch unmitigated damage values from FFLogs."""
    logger.info("[fetch_damage] boss=%s", state["boss_name"])
    t0 = time.monotonic()
    
    from xiv_timeline.models import resolve_boss_name
    from xiv_timeline.fflogs_client import FFLogsClient

    boss_info = resolve_boss_name(state["boss_name"])
    damage_data = {}
    
    if boss_info and "fflogs_id" in boss_info:
        encounter_id = boss_info["fflogs_id"]
        logger.info(f"[fetch_damage] Found fflogs_id {encounter_id}")
        
        client = FFLogsClient()
        try:
            results = await client.get_boss_damage_values(encounter_id)
            # Serialize for state representation
            for name, stat in results.items():
                damage_data[name] = stat.model_dump()
                
            logger.info(
                "[fetch_damage] Fetched %d damage stats in %.2fs",
                len(damage_data),
                time.monotonic() - t0,
            )
        except Exception as exc:
            logger.warning("[fetch_damage] Failed: %s", exc)
        finally:
            await client.close()
    else:
        logger.info("[fetch_damage] No fflogs_id mapped for %s", state["boss_name"])
        
    return {"damage_data": damage_data}


async def fetch_cactbot_node(state: TimelineState) -> dict[str, Any]:
    """Fetch timeline data from the cactbot GitHub repository."""
    logger.info(
        "[fetch_cactbot] boss=%s expansion=%s",
        state["boss_name"],
        state.get("expansion"),
    )
    t0 = time.monotonic()
    client = CactbotClient()
    try:
        data = await client.fetch_timeline(
            boss_name=state["boss_name"],
            expansion=state.get("expansion"),
            encounter_type=state.get("encounter_type"),
            difficulty=state.get("difficulty"),
        )
        logger.info(
            "[fetch_cactbot] Done in %.2fs — %d entries, %d phases",
            time.monotonic() - t0,
            len(data.get("entries", [])),
            len(data.get("phases", [])),
        )
        return {
            "cactbot_data": data,
            "cactbot_raw": data.get("raw_content", ""),
        }
    except Exception as exc:
        logger.error("[fetch_cactbot] Failed: %s", exc)
        raise
    finally:
        await client.close()


async def fetch_guides_node(state: TimelineState) -> dict[str, Any]:
    """Fetch strategy guides via the LLM-driven GuideAgent."""
    logger.info("[fetch_guides] boss=%s", state["boss_name"])
    t0 = time.monotonic()
    agent = GuideAgent()
    try:
        data = await agent.fetch_all_guides(state["boss_name"])
        guides = data.get("guides", {})
        ok = [s for s, g in guides.items() if g.get("success")]
        logger.info(
            "[fetch_guides] Done in %.2fs — succeeded: %s",
            time.monotonic() - t0,
            ok or "none",
        )
        return {"guide_data": data}
    except Exception as exc:
        logger.error("[fetch_guides] Failed: %s", exc)
        raise
    finally:
        await agent.close()


async def synthesize_node(state: TimelineState) -> dict[str, Any]:
    """Use the LLM to synthesize a structured timeline from fetched data."""
    logger.info("[synthesize] boss=%s", state["boss_name"])
    t0 = time.monotonic()

    cactbot_data = state["cactbot_data"]
    guide_data = state["guide_data"]

    # Deterministic baseline from local synthesizer
    synthesizer = TimelineSynthesizer()
    local_result = synthesizer.synthesize(cactbot_data, guide_data)

    # Build LLM prompt
    entries_summary = _summarize_entries(cactbot_data.get("entries", []))
    guide_summary = _summarize_guides(guide_data)
    damage_summary = _summarize_damage(state.get("damage_data", {}))

    prompt = (
        f"Generate a synthesized timeline for the FFXIV boss: {state['boss_name']}.\n\n"
        f"## Cactbot Timeline Data\n{entries_summary}\n\n"
        f"## Strategy Guide Content\n{guide_summary}\n\n"
        f"## Damage Profile Data (from 10 FFLogs reports)\n{damage_summary}\n\n"
        f"Set expansion={cactbot_data.get('expansion', 'unknown')}, "
        f"difficulty={cactbot_data.get('difficulty', 'unknown')}. "
        f"Set generated_at to: {datetime.now().isoformat()}."
    )

    try:
        llm = get_llm()
        parser = PydanticOutputParser(pydantic_object=SynthesizedTimeline)
        full_prompt = prompt + "\n\n" + parser.get_format_instructions()

        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=full_prompt),
        ])

        content = str(response.content)
        if "</think>" in content:
            content = content.split("</think>")[-1].strip()

        result: SynthesizedTimeline = parser.invoke(content)
        synthesized = result.model_dump()
        
        # Post-process to guarantee --sync-- is removed
        for phase in synthesized.get("phases", []):
            phase["entries"] = [
                e for e in phase.get("entries", [])
                if e.get("ability_name") != "--sync--"
            ]
            
        logger.info(
            "[synthesize] LLM returned %d phases in %.2fs",
            len(synthesized.get("phases", [])),
            time.monotonic() - t0,
        )
    except Exception as exc:
        logger.warning("[synthesize] LLM failed (%s), using local synthesis", exc)
        synthesized = local_result

    synthesized.setdefault("generated_at", datetime.now().isoformat())
    return {"synthesized": synthesized}

def _get_base_ability_name(name: str) -> str:
    """Strip numbered suffixes and parenthetical variants from an ability name.

    Examples:
        'Flame Floater 1'       -> 'Flame Floater'
        'Xtreme Spectacular (line)' -> 'Xtreme Spectacular'
        'Xtreme Spectacular x6' -> 'Xtreme Spectacular'
        'Hot Aerial 3'          -> 'Hot Aerial'
        'Cutback Blaze'         -> 'Cutback Blaze'
    """
    import re
    # Strip trailing parenthetical like " (line)", " (big)", " (cast)"
    name = re.sub(r'\s*\([^)]*\)\s*$', '', name)
    # Strip trailing x-multiplier suffix like " x6", " x12"
    name = re.sub(r'\s+x\d+$', '', name, flags=re.IGNORECASE)
    # Strip trailing number suffix like " 1", " 2", " 12"
    name = re.sub(r'\s+\d+$', '', name)
    return name.strip()


def _group_multi_hit_entries(
    entries: list[dict[str, Any]],
    threshold: float,
) -> list[dict[str, Any]]:
    """Consolidate consecutive same-base-name entries into grouped entries.

    Entries whose base ability name matches (after stripping numbered suffixes
    and parenthetical variants) and that are within *threshold* seconds of
    each other (measured between consecutive hits) are merged into a single
    entry with ``hit_count``, ``time_range_start``, and ``time_range_end``.
    """
    if not entries:
        return entries

    result: list[dict[str, Any]] = []
    group: list[dict[str, Any]] = [entries[0]]

    for entry in entries[1:]:
        prev = group[-1]
        prev_base = _get_base_ability_name(prev.get("ability_name", ""))
        curr_base = _get_base_ability_name(entry.get("ability_name", ""))

        same_base = prev_base.lower() == curr_base.lower()
        within_threshold = (
            abs(entry.get("timestamp", 0) - prev.get("timestamp", 0)) <= threshold
        )

        if same_base and within_threshold:
            group.append(entry)
        else:
            result.append(_finalize_hit_group(group))
            group = [entry]

    result.append(_finalize_hit_group(group))
    return result


def _extract_xn_multiplier(name: str) -> int:
    """Extract the xN multiplier from an ability name, if present.

    Examples:
        'Xtreme Spectacular x6' -> 6
        'Epic Brotherhood x2'   -> 2
        'Hot Impact'             -> 0  (no multiplier)
    """
    import re
    m = re.search(r'\bx(\d+)$', name, flags=re.IGNORECASE)
    return int(m.group(1)) if m else 0


def _finalize_hit_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse a group of same-name entries into one representative entry.

    ``hit_count`` accounts for xN multipliers embedded in ability names.
    For entries whose name includes an xN suffix (e.g. "Xtreme Spectacular x6"),
    that multiplier is added to the group size.
    """
    if len(group) == 1:
        entry = group[0]
        # Even a single entry may carry an xN multiplier
        xn = _extract_xn_multiplier(entry.get("ability_name", ""))
        if xn > 0:
            entry = entry.copy()
            entry["hit_count"] = xn
        return entry

    first = group[0].copy()
    base_name = _get_base_ability_name(first.get("ability_name", ""))
    first["ability_name"] = base_name

    # Sum: each entry counts as 1, but entries with xN suffix count as N instead
    total_hits = 0
    for e in group:
        xn = _extract_xn_multiplier(e.get("ability_name", ""))
        total_hits += xn if xn > 0 else 1

    first["hit_count"] = total_hits
    first["time_range_start"] = group[0].get("timestamp")
    first["time_range_end"] = group[-1].get("timestamp")
    return first


async def append_damage_node(state: TimelineState) -> dict[str, Any]:
    """Append damage data to the synthesized timeline."""
    logger.info("[append_damage] Merging damage data into timeline")
    
    synthesized = state.get("synthesized", {})
    damage_data = state.get("damage_data", {})
    
    if not damage_data or not synthesized:
        return {"synthesized": synthesized}

    # Create a secondary lookup for case-insensitive matching
    lower_damage_data = {k.lower(): v for k, v in damage_data.items()}

    matched_count = 0
    for phase in synthesized.get("phases", []):
        for entry in phase.get("entries", []):
            name = entry.get("ability_name")
            if not name:
                continue
                
            # Clean cactbot specific suffixes for better matching
            clean_name = name.lower().replace("(cast)", "").replace("(damage)", "").replace("(enrage)", "").replace(" (", "(").strip()
            
            # Also try the base name (without number / parenthetical suffix)
            base_name = _get_base_ability_name(name).lower()
            
            # Cactbot sometimes has "AbilityA/AbilityB", check both
            sub_names = [n.strip() for n in clean_name.split("/")]
            # Add base name as an extra lookup candidate
            if base_name not in sub_names:
                sub_names.append(base_name)
            
            matched_dmg = None
            for sub_name in sub_names:
                if sub_name in lower_damage_data:
                    matched_dmg = lower_damage_data[sub_name]
                    break
                    
            if matched_dmg is not None:
                # Core damage fields
                entry["unmitigated_damage"] = matched_dmg.get("unmitigated_damage_70th")
                entry["ability_type"] = matched_dmg.get("ability_type") or entry.get("ability_type")
                entry["is_dot"] = matched_dmg.get("is_dot")
                # Enriched mitigation fields
                entry["damage_min"] = matched_dmg.get("damage_min")
                entry["damage_max"] = matched_dmg.get("damage_max")
                entry["damage_median"] = matched_dmg.get("damage_median")
                entry["target_count"] = matched_dmg.get("target_count_avg")
                entry["hits_per_cast"] = matched_dmg.get("hits_per_cast")
                matched_count += 1
                
    logger.info("[append_damage] Attached damage values to %d timeline entries", matched_count)

    # Build timeline-ordered FFLogs reference (all entries, pre-filter)
    import copy
    fflogs_reference: list[dict[str, Any]] = []
    for phase in synthesized.get("phases", []):
        for entry in phase.get("entries", []):
            ref_entry = copy.deepcopy(entry)
            ref_entry["phase"] = phase.get("name", "Unknown")
            fflogs_reference.append(ref_entry)
    fflogs_reference.sort(key=lambda e: e.get("timestamp", 0))

    # Filter out entries without damage values
    for phase in synthesized.get("phases", []):
        phase["entries"] = [
            e for e in phase.get("entries", [])
            if e.get("unmitigated_damage") is not None
        ]

    # Group consecutive same-name multi-hit entries within each phase
    from xiv_timeline.models import MULTI_HIT_GROUP_THRESHOLD
    for phase in synthesized.get("phases", []):
        phase["entries"] = _group_multi_hit_entries(
            phase.get("entries", []),
            threshold=MULTI_HIT_GROUP_THRESHOLD,
        )

    # Remove empty phases
    synthesized["phases"] = [
        p for p in synthesized.get("phases", [])
        if p.get("entries")
    ]

    filtered_total = sum(len(p.get("entries", [])) for p in synthesized.get("phases", []))
    logger.info("[append_damage] %d entries remain after filtering and grouping", filtered_total)

    return {"synthesized": synthesized, "fflogs_reference": fflogs_reference}


async def export_node(state: TimelineState) -> dict[str, Any]:
    """Generate cactbot-compatible timeline export text."""
    logger.info("[export] Generating cactbot export")
    synthesizer = TimelineSynthesizer()
    cactbot_export = synthesizer.generate_cactbot_export(state["synthesized"])
    logger.info("[export] %d chars of export text", len(cactbot_export))
    return {"cactbot_export": cactbot_export}


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------


def _summarize_entries(entries: list[dict[str, Any]], max_entries: int = 80) -> str:
    """Create a concise text summary of cactbot entries for the LLM prompt."""
    if not entries:
        return "(no timeline entries found)"

    lines: list[str] = []
    for entry in entries[:max_entries]:
        ts = entry.get("timestamp", 0)
        name = entry.get("ability_name", "?")
        hit_info = ""
        if entry.get("is_multi_hit"):
            hit_info = f" (x{entry.get('hit_count', 1)} hits)"
        lines.append(f"  {ts:>7.1f}s  {name}{hit_info}")

    if len(entries) > max_entries:
        lines.append(f"  ... and {len(entries) - max_entries} more entries")
    return "\n".join(lines)


def _summarize_guides(guide_data: dict[str, Any]) -> str:
    """Create a text summary of guide content for the LLM prompt."""
    parts: list[str] = []
    for source, data in guide_data.get("guides", {}).items():
        if not data.get("success"):
            parts.append(f"[{source}]: no guide found")
            continue
        content = data.get("content", {})
        overview = content.get("overview", "")
        phases = content.get("phases", [])
        mechanics = content.get("mechanics", [])

        parts.append(f"[{source}] Overview: {overview[:300]}")
        for phase in phases[:5]:
            title = phase.get("title", "")
            text = phase.get("content", "")[:200]
            parts.append(f"  Phase: {title} — {text}")

        if mechanics:
            parts.append("  Mechanics:")
            for mech in mechanics[:20]:
                name = mech.get("name", "")
                desc = mech.get("description", "")[:150]
                parts.append(f"    - {name}: {desc}")

    return "\n".join(parts) if parts else "(no guide content)"


def _summarize_damage(damage_data: dict[str, Any]) -> str:
    """Create a text summary of damage profile data for the LLM prompt."""
    if not damage_data:
        return "(no damage data available)"

    lines: list[str] = []
    # Sort by damage to show highest-damage abilities first
    sorted_abilities = sorted(
        damage_data.items(),
        key=lambda x: x[1].get("unmitigated_damage_70th", 0) if isinstance(x[1], dict) else 0,
        reverse=True,
    )

    for name, stat in sorted_abilities[:30]:
        if not isinstance(stat, dict):
            continue
        dmg = stat.get("unmitigated_damage_70th", 0)
        d_min = stat.get("damage_min", 0)
        d_max = stat.get("damage_max", 0)
        ab_type = stat.get("ability_type", "Unknown")
        is_dot = stat.get("is_dot", False)
        targets = stat.get("target_count_avg", 0)
        samples = stat.get("damage_samples", 0)

        type_str = f" [{ab_type}]" if ab_type else ""
        dot_str = " (DOT)" if is_dot else ""
        lines.append(
            f"  {name}{type_str}{dot_str}: ~{dmg:,.0f} dmg "
            f"(range: {d_min:,.0f}-{d_max:,.0f}, targets: {targets:.1f}, "
            f"hits/cast: {stat.get('hits_per_cast', 1.0):.1f}, samples: {samples})"
        )

    return "\n".join(lines) if lines else "(no damage data available)"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """Build and compile the timeline generation graph.

    fetch_cactbot → fetch_guides → synthesize → export
    """
    builder = StateGraph(TimelineState)

    builder.add_node("fetch_cactbot", fetch_cactbot_node)
    builder.add_node("fetch_guides", fetch_guides_node)
    builder.add_node("synthesize", synthesize_node)
    builder.add_node("fetch_damage", fetch_damage_node)
    builder.add_node("append_damage", append_damage_node)
    builder.add_node("export", export_node)

    builder.add_edge(START, "fetch_cactbot")
    builder.add_edge(START, "fetch_damage")
    builder.add_edge("fetch_cactbot", "fetch_guides")
    builder.add_edge("fetch_guides", "synthesize")
    
    # Wait for both synthesize and fetch_damage to finish before appending
    builder.add_node("join_node", lambda state: state)

    builder.add_edge("synthesize", "join_node")
    builder.add_edge("fetch_damage", "join_node")
    builder.add_edge("join_node", "append_damage")
    
    builder.add_edge("append_damage", "export")
    builder.add_edge("export", END)

    return builder.compile()


timeline_graph = build_graph()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run_timeline_generation(
    boss_name: str,
    expansion: str | None = None,
    encounter_type: str | None = None,
    difficulty: str | None = None,
) -> dict[str, Any]:
    """Run the complete timeline generation pipeline.

    Returns dict with keys: synthesized, cactbot_export, cactbot_raw.
    """
    result = await timeline_graph.ainvoke({
        "boss_name": boss_name,
        "expansion": expansion,
        "encounter_type": encounter_type,
        "difficulty": difficulty,
    })

    return {
        "synthesized": result["synthesized"],
        "cactbot_export": result["cactbot_export"],
        "cactbot_raw": result["cactbot_raw"],
        "damage_data": result.get("damage_data", {}),
        "fflogs_reference": result.get("fflogs_reference", []),
    }
