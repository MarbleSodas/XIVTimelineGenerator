#!/usr/bin/env python3
"""Test the LLM-based description generation with M11S video."""

import sys
import os
sys.path.insert(0, "/Users/eugene/Documents/Github/XIVTimelineGenerator")

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Set up MiniMax API key
os.environ["MINIMAX_API_KEY"] = os.environ.get("MINIMAX_API_KEY", "")

from config import config
from agents.youtube_guide_agent import YouTubeGuideDiscoveryAgent
from agents.transcript_enrichment_orchestrator import TranscriptEnrichmentOrchestrator
from schemas.cactbot_schemas import CactbotTimelineEntry
from schemas.aggregation_schemas import AggregatedAction

VIDEO_ID = "w1uuwzhyf5A"

print(f"Testing LLM-based description generation")
print("=" * 60)

# Check for API key
api_key = os.environ.get("MINIMAX_API_KEY", "")
if not api_key:
    print("WARNING: MINIMAX_API_KEY not set, LLM won't work")
    print("Set it with: export MINIMAX_API_KEY=your_key")
else:
    print(f"API key found: {api_key[:10]}...")

# Get LLM clients - one wrapped for atomic agents, one raw for direct API calls
llm_client = None
raw_llm_client = None
try:
    llm_client = config.get_llm_client()
    raw_llm_client = config.get_raw_client()
    print(f"LLM client (instructor): {type(llm_client)}")
    print(f"LLM client (raw): {type(raw_llm_client)}")
except Exception as e:
    print(f"Failed to get LLM client: {e}")

# Fetch transcript
guide_agent = YouTubeGuideDiscoveryAgent(api_key=None)

try:
    transcript = guide_agent.get_transcript_only(VIDEO_ID)
    
    if not transcript:
        print("No transcript found")
        sys.exit(1)
    
    print(f"\nGot transcript!")
    print(f"  Title: {transcript.video_metadata.title}")
    print(f"  Segments: {len(transcript.segments)}")
    
    # Create mock cactbot entries (simulating M11S timeline)
    # These are actual M11S abilities
    cactbot_entries = [
        CactbotTimelineEntry(time=10.4, name="Frontal Cleave", original_name="Frontal Cleave"),
        CactbotTimelineEntry(time=20.1, name="Dark Force", original_name="Dark Force"),
        CactbotTimelineEntry(time=25.3, name="Soul Rush", original_name="Soul Rush"),
        CactbotTimelineEntry(time=35.0, name="Dimension Slash", original_name="Dimension Slash"),
        CactbotTimelineEntry(time=45.2, name="Raidwide", original_name="Raidwide"),
        CactbotTimelineEntry(time=55.8, name="Tank Buster", original_name="Tank Buster"),
        CactbotTimelineEntry(time=65.1, name="Stack Marker", original_name="Stack Marker"),
        CactbotTimelineEntry(time=75.4, name="Spread", original_name="Spread"),
    ]
    
    # Mock aggregated actions
    aggregated_actions = [
        AggregatedAction(
            id="frontal_cleave_1",
            name="Frontal Cleave",
            time=10.4,
            occurrence=1,
            unmitigated_damage="35000",
            damage_type="physical",
            is_tank_buster=False,
            is_raidwide=False,
        ),
        AggregatedAction(
            id="dark_force_1",
            name="Dark Force",
            time=20.1,
            occurrence=1,
            unmitigated_damage="45000",
            damage_type="magical",
            is_tank_buster=True,
            is_raidwide=False,
        ),
        AggregatedAction(
            id="soul_rush_1",
            name="Soul Rush",
            time=25.3,
            occurrence=1,
            unmitigated_damage="38000",
            damage_type="magical",
            is_tank_buster=True,
            is_raidwide=False,
        ),
        AggregatedAction(
            id="dimension_slash_1",
            name="Dimension Slash",
            time=35.0,
            occurrence=1,
            unmitigated_damage="42000",
            damage_type="magical",
            is_tank_buster=True,
            is_raidwide=False,
        ),
        AggregatedAction(
            id="raidwide_1",
            name="Raidwide",
            time=45.2,
            occurrence=1,
            unmitigated_damage="28000",
            damage_type="magical",
            is_tank_buster=False,
            is_raidwide=True,
        ),
    ]
    
    print(f"\nMock timeline: {len(cactbot_entries)} abilities")
    for e in cactbot_entries:
        print(f"  {e.time}s - {e.name}")
    
    # Test the enrichment
    print("\n" + "=" * 60)
    print("Running transcript enrichment...")
    print("=" * 60)
    
    orchestrator = TranscriptEnrichmentOrchestrator(
        llm_client=llm_client,
        raw_llm_client=raw_llm_client,
        model=config.llm_model,
        youtube_api_key=None,
    )
    
    # Run enrichment
    from schemas.youtube_schemas import TimelineEnrichmentInput
    
    enrichment_input = TimelineEnrichmentInput(
        boss_id="r11s",
        boss_name="The Tyrant",
        base_timeline=[],
        youtube_video_ids=[VIDEO_ID],
        include_variants=True,
    )
    
    result = orchestrator.run(
        enrichment_input,
        cactbot_entries,
        aggregated_actions,
        [],
    )
    
    print(f"\nEnrichment result:")
    print(f"  Enriched actions: {len(result.enriched_actions)}")
    print(f"  Transcripts used: {result.transcripts_used}")
    
    print("\n--- Generated Descriptions ---")
    for action in result.enriched_actions[:10]:
        print(f"\n{action.name} @ {action.time}s:")
        print(f"  Description: {action.transcript_description}")
        print(f"  Damage type: {action.damage_type}")
        print(f"  Tank buster: {action.is_tank_buster}")
    
    orchestrator.close()
    guide_agent.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
