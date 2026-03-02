#!/usr/bin/env python3
"""
Test script for YouTube transcript enrichment feature.
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from tools.youtube_transcript import YouTubeTranscriptFetcher, YouTubeTranscriptError
from agents.description_generator_agent import TranscriptDescriptionGenerator
from schemas.cactbot_schemas import CactbotTimelineEntry
from schemas.aggregation_schemas import AggregatedAction


def test_youtube_transcript():
    """Test fetching YouTube transcript."""
    print("=" * 60)
    print("Testing YouTube Transcript Fetching")
    print("=" * 60)
    
    fetcher = YouTubeTranscriptFetcher()
    
    # Test with a sample video that has captions
    # Using a well-known video with English captions
    test_video_ids = [
        "dQw4w9WgXcQ",  # Rick Astley - always has captions
    ]
    
    for video_id in test_video_ids:
        print(f"\nTesting video: {video_id}")
        try:
            # Get metadata first
            metadata = fetcher.get_video_metadata(video_id)
            print(f"  Title: {metadata.get('title', 'N/A')}")
            print(f"  Channel: {metadata.get('channel', 'N/A')}")
            
            # Try to fetch transcript
            transcript = fetcher.fetch_transcript(video_id, languages=["en"])
            print(f"  Transcript segments: {len(transcript)}")
            
            if transcript:
                print(f"  First segment: {transcript[0]['text'][:50]}...")
                
        except YouTubeTranscriptError as e:
            print(f"  Error: {e}")
        except Exception as e:
            print(f"  Unexpected error: {e}")
    
    fetcher.close()
    print()


def test_description_generation():
    """Test description generation with and without transcripts."""
    print("=" * 60)
    print("Testing Description Generation")
    print("=" * 60)
    
    generator = TranscriptDescriptionGenerator(llm_client=None)
    
    test_abilities = [
        "Flame Floater",
        "Tank Buster",
        "Stack Marker",
        "Raidwide",
        "Frontal Cleave",
    ]
    
    print("\n--- Rule-based descriptions (no LLM) ---")
    for ability in test_abilities:
        desc = generator._simple_description(ability)
        print(f"  {ability}: {desc}")
    
    print()


def test_aggregator_damage_type():
    """Test that damage type is properly set in aggregated actions."""
    print("=" * 60)
    print("Testing Aggregator Damage Type")
    print("=" * 60)
    
    from agents.aggregator_agent import TimelineAggregatorAgent
    from schemas.damage_schemas import DamageEvent
    
    aggregator = TimelineAggregatorAgent()
    
    # Create sample damage events with different hit types
    # Hit type 1, 2 = physical
    # Hit type 4, 8, 9, 10 = magical
    sample_events = [
        DamageEvent(
            timestamp=10.0,
            ability_name="Test Physical",
            ability_id=1234,
            unmitigated_damage=50000,
            damage_type="physical",  # From hit type 1 or 2
            target_id=1,
            source_id=999,
            report_code="test1",
        ),
        DamageEvent(
            timestamp=20.0,
            ability_name="Test Magical",
            ability_id=5678,
            unmitigated_damage=75000,
            damage_type="magical",  # From hit type 4, 8, 9, or 10
            target_id=1,
            source_id=999,
            report_code="test2",
        ),
    ]
    
    # Create sample cactbot timeline entries
    timeline_entries = [
        CactbotTimelineEntry(
            time=10.0,
            name="Test Physical",
            original_name="Test Physical",
            is_commented=False,
        ),
        CactbotTimelineEntry(
            time=20.0,
            name="Test Magical",
            original_name="Test Magical",
            is_commented=False,
        ),
    ]
    
    # Run aggregation
    result = aggregator.run(sample_events, timeline_entries)
    
    print(f"\nAggregated {len(result.aggregated_actions)} actions:")
    for action in result.aggregated_actions:
        print(f"  {action.name}: damage_type={action.damage_type}, damage={action.unmitigated_damage}")
    
    print()


def test_orchestrator_integration():
    """Test that the orchestrator has the new YouTube integration."""
    print("=" * 60)
    print("Testing Orchestrator Integration")
    print("=" * 60)
    
    from agents.orchestrator import TimelineGenerationOrchestrator
    import inspect
    
    # Check that the orchestrator has the new parameters
    init_sig = inspect.signature(TimelineGenerationOrchestrator.__init__)
    print("\nTimelineGenerationOrchestrator.__init__ parameters:")
    for param in init_sig.parameters:
        print(f"  - {param}")
    
    # Check that run method accepts youtube_video_ids
    from schemas.timeline_schemas import TimelineGenerationRequest
    request_fields = TimelineGenerationRequest.model_fields
    print("\nTimelineGenerationRequest fields:")
    for field in request_fields:
        print(f"  - {field}")
    
    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("YouTube Enrichment Feature Tests")
    print("=" * 60 + "\n")
    
    # Run tests
    test_youtube_transcript()
    test_description_generation()
    test_aggregator_damage_type()
    test_orchestrator_integration()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
