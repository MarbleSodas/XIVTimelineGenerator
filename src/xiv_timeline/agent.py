"""Pydantic AI agent for timeline generation with Minimax M2.5 support."""

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from xiv_timeline.cactbot_client import CactbotClient
from xiv_timeline.guide_scraper import GuideScraper
from xiv_timeline.synthesizer import TimelineSynthesizer


# Output types for structured response
class TimelinePhase(BaseModel):
    """A phase in the boss encounter."""

    name: str
    start_time: float
    end_time: float
    duration: float | None
    ability_count: int
    tips: list[str]


class TimelineVariation(BaseModel):
    """A variation or phase skip in the timeline."""

    source: str
    title: str
    description: str
    type: str


class AbilityTargetInfo(BaseModel):
    """Information about a boss ability's target and hit count."""

    ability_name: str
    target_type: str  # e.g., "raidwide", "single_tank", "pair", "random"
    hit_count: int
    target_name: str | None = None  # Specific target if known
    notes: str | None = None


class SynthesizedTimeline(BaseModel):
    """Complete synthesized timeline for a boss."""

    boss_name: str
    expansion: str
    encounter_type: str
    difficulty: str
    phases: list[TimelinePhase]
    variations: list[TimelineVariation]
    notes: list[str]
    confidence: float
    generated_at: str
    sources: dict[str, Any]
    # New multi-hit and target info fields
    ability_targets: list[AbilityTargetInfo] = []
    multi_hit_abilities: list[dict[str, Any]] = []


# Agent dependencies
class AgentDeps:
    """Dependencies for the timeline agent."""

    def __init__(self, cactbot_client: "CactbotClient", guide_scraper: "GuideScraper", synthesizer: "TimelineSynthesizer"):
        self.cactbot_client = cactbot_client
        self.guide_scraper = guide_scraper
        self.synthesizer = synthesizer

    cactbot_client: "CactbotClient"
    guide_scraper: "GuideScraper"
    synthesizer: "TimelineSynthesizer"
    """Dependencies for the timeline agent."""

    cactbot_client: CactbotClient
    guide_scraper: GuideScraper
    synthesizer: TimelineSynthesizer


def create_model() -> OpenAIChatModel:
    """
    Create the Minimax M2.5 model configuration.

    Configure via environment variables:
    - MINIMAX_API_KEY: Your Minimax API key
    - MINIMAX_BASE_URL: Custom endpoint (default: https://api.minimax.chat/v1)
    - MINIMAX_MODEL: Model name (default: MiniMax-M2.5)
    """
    api_key = os.getenv("MINIMAX_API_KEY", "your-api-key-here")
    base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.chat/v1")
    model_name = os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")

    return OpenAIChatModel(
        model_name,
        provider=OpenAIProvider(
            base_url=base_url,
            api_key=api_key,
        ),
    )


# System prompt for the agent
SYSTEM_PROMPT = """You are an expert FFXIV raid timeline generator. Your task is to synthesize
accurate boss timelines by combining data from cactbot (community timeline repository) with
strategy guides from popular websites like Icy Veins and Hardcore Gamer.

You have access to tools that can:
1. Fetch raw timeline data from cactbot GitHub repository
2. Scrape boss guides from Icy Veins and Hardcore Gamer
3. Research boss ability targets and hit counts

When generating timelines:
- Parse the cactbot timeline entries carefully
- Cross-reference with guide information for phase breakdowns
- Identify variations (phase skips, timing differences)
- Note important mechanics and their explanations
- Provide accurate timestamps from the cactbot data

Output a structured timeline with:
- Clear phase definitions with start/end times
- Notable ability sequences
- Any known variations or skips
- Helpful tips from the guides
- Confidence level based on available data

Always prioritize cactbot timestamps for accuracy, use guides for context and variations."""


# Create the agent
_timeline_agent: Agent[AgentDeps] | None = None


def get_agent() -> Agent[AgentDeps]:
    """Get or create the timeline agent."""
    global _timeline_agent
    if _timeline_agent is None:
        _timeline_agent = Agent(
            model=create_model(),
            deps_type=AgentDeps,
            output_type=SynthesizedTimeline,
            instructions=SYSTEM_PROMPT,
        )
    return _timeline_agent


# Tool functions
async def fetch_cactbot_timeline(
    ctx: RunContext[AgentDeps],
    boss_name: str,
    expansion: str | None = None,
    encounter_type: str | None = None,
    difficulty: str | None = None,
) -> dict[str, Any]:
    """
    Fetch timeline data from cactbot GitHub repository.

    Args:
        boss_name: Boss name or ID (e.g., "p12s", "Zodiark")
        expansion: Expansion code (e.g., "06-ew")
        encounter_type: Type of encounter (raid, trial, ultimate)
        difficulty: Difficulty (n, s, u)

    Returns:
        Dictionary containing timeline data
    """
    return await ctx.deps.cactbot_client.fetch_timeline(
        boss_name=boss_name,
        expansion=expansion,
        encounter_type=encounter_type,
        difficulty=difficulty,
    )


async def fetch_guide_content(
    ctx: RunContext[AgentDeps],
    boss_name: str,
    source: str = "icyveins",
) -> dict[str, Any]:
    """
    Fetch boss guide from strategy websites.

    Args:
        boss_name: Name of the boss
        source: Guide source (icyveins, hardcoregamer)

    Returns:
        Dictionary containing guide content
    """
    scraper = ctx.deps.guide_scraper

    if source.lower() in ["icyveins", "icy-veins"]:
        return await scraper.fetch_icyveins_guide(boss_name)
    elif source.lower() in ["hardcoregamer", "hardcore-gamer"]:
        return await scraper.fetch_hardcoregamer_guide(boss_name)
    else:
        return await scraper.fetch_all_guides(boss_name)


async def synthesize_timeline(
    ctx: RunContext[AgentDeps],
    cactbot_data: dict[str, Any],
    guide_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Synthesize timeline from cactbot and guide data.

    Args:
        cactbot_data: Raw timeline from cactbot
        guide_data: Guide content

    Returns:
        Synthesized timeline
    """
    return ctx.deps.synthesizer.synthesize(cactbot_data, guide_data)


async def research_ability_targets(
    boss_name: str,
    abilities: list[dict[str, Any]],
    guide_data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Research target information for boss abilities."""
    from xiv_timeline.models import infer_target_type, TargetType
    
    target_info = []
    
    # Get unique ability names
    unique_abilities = {}
    for ability in abilities:
        name = ability.get("ability_name", "")
        if name not in unique_abilities:
            unique_abilities[name] = ability
    
    # Extract target info from guide data
    guides = guide_data.get("guides", {})
    icyveins = guides.get("icy-veins", {}).get("content", {})
    
    # Build target info for each unique ability
    for ability_name, ability in unique_abilities.items():
        # Start with inference from ability name
        target_type = infer_target_type(ability_name)
        
        # Check guide content for specific mechanics
        notes = []
        
        # Look through guide content for mentions of this ability
        guide_content = str(icyveins.get("overview", ""))
        if ability_name.lower() in guide_content.lower():
            notes.append("Found in guide overview")
        
        # Look through phase content
        for phase in icyveins.get("phases", []):
            phase_content = str(phase.get("content", ""))
            if ability_name.lower() in phase_content.lower():
                notes.append(f"Found in {phase.get('title', 'phase')} section")
        
        info = {
            "ability_name": ability_name,
            "target_type": target_type.value if target_type else TargetType.UNKNOWN.value,
            "hit_count": ability.get("hit_count", 1),
            "is_multi_hit": ability.get("is_multi_hit", False),
            "target_name": ability.get("target"),
            "notes": "; ".join(notes) if notes else None,
        }
        target_info.append(info)
    
    return target_info


# Register tools with the agent
_agent = get_agent()


@_agent.tool
async def fetch_cactbot_timeline_tool(
    ctx: RunContext[AgentDeps],
    boss_name: str,
    expansion: str | None = None,
    encounter_type: str | None = None,
    difficulty: str | None = None,
) -> dict[str, Any]:
    """Fetch timeline data from cactbot repository."""
    return await fetch_cactbot_timeline(ctx, boss_name, expansion, encounter_type, difficulty)


@_agent.tool
async def fetch_guide_content_tool(
    ctx: RunContext[AgentDeps],
    boss_name: str,
    source: str = "all",
) -> dict[str, Any]:
    """Fetch boss guide from strategy websites."""
    return await fetch_guide_content(ctx, boss_name, source)


async def run_timeline_generation(
    boss_name: str,
    expansion: str | None = None,
    encounter_type: str | None = None,
    difficulty: str | None = None,
) -> dict[str, Any]:
    """
    Run the complete timeline generation pipeline.

    Args:
        boss_name: Boss name or ID
        expansion: Expansion code
        encounter_type: Type of encounter
        difficulty: Difficulty level

    Returns:
        Complete timeline data with JSON and cactbot export
    """
    # Initialize dependencies
    cactbot_client = CactbotClient()
    guide_scraper = GuideScraper()
    synthesizer = TimelineSynthesizer()

    deps = AgentDeps(
        cactbot_client=cactbot_client,
        guide_scraper=guide_scraper,
        synthesizer=synthesizer,
    )

    try:
        # Fetch cactbot data
        cactbot_data = await cactbot_client.fetch_timeline(
            boss_name=boss_name,
            expansion=expansion,
            encounter_type=encounter_type,
            difficulty=difficulty,
        )

        # Fetch guide data
        guide_data = await guide_scraper.fetch_all_guides(boss_name)

        # Synthesize
        synthesized = synthesizer.synthesize(cactbot_data, guide_data)
        
        # Research ability targets and hit counts
        ability_targets = await research_ability_targets(
            boss_name,
            cactbot_data.get("entries", []),
            guide_data,
        )
        
        # Add ability targets to synthesized data
        synthesized["ability_targets"] = ability_targets
        
        # Extract multi-hit abilities
        multi_hit_abilities = [
            at for at in ability_targets if at.get("is_multi_hit", False)
        ]
        synthesized["multi_hit_abilities"] = multi_hit_abilities

        # Generate cactbot export
        cactbot_export = synthesizer.generate_cactbot_export(synthesized)

        return {
            "synthesized": synthesized,
            "cactbot_export": cactbot_export,
            "cactbot_raw": cactbot_data.get("raw_content", ""),
        }

    finally:
        await cactbot_client.close()
        await guide_scraper.close()
