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
    ability_id: str | None = None
    source: str | None = None
    cast_duration: float | None = None
    description: str | None = None
    unmitigated_damage: float | None = None
    ability_type: str | None = None
    is_dot: bool | None = None
    # Mitigation planning fields
    damage_min: float | None = None
    damage_max: float | None = None
    damage_median: float | None = None
    target_count: float | None = None
    mitigation_note: str | None = None


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
- Use cactbot timestamps as the source of truth for timing.
- Use guide content for phase context, detailed mechanic descriptions, and tips.
- Identify phase boundaries and group abilities into phases.
- Write concise, actionable tips for each phase.
- Provide detailed and helpful descriptions for the boss actions in `description` using the mechanics information.
- The `--sync--` action helps signify phase boundaries, but you should NEVER output `--sync--` in the actual timeline output entries.
- Set confidence based on how much data was available.
- When damage data is available, prioritize describing high-damage abilities and note mitigation requirements.
- For mitigation_note, suggest specific mitigation actions (e.g. Reprisal, Shield Samba, Kerachole) for abilities dealing significant damage.

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
            
            # Cactbot sometimes has "AbilityA/AbilityB", check both
            sub_names = [n.strip() for n in clean_name.split("/")]
            
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
                # Set ability_id from FFLogs hex if not already set
                if not entry.get("ability_id") and matched_dmg.get("ability_game_id"):
                    entry["ability_id"] = matched_dmg.get("ability_game_id")
                matched_count += 1
                
    logger.info("[append_damage] Attached damage values to %d timeline entries", matched_count)
    return {"synthesized": synthesized}


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
            f"(range: {d_min:,.0f}-{d_max:,.0f}, targets: {targets:.1f}, samples: {samples})"
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
    }
