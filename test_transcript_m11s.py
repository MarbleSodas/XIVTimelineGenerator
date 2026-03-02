#!/usr/bin/env python3
"""Quick test to fetch YouTube transcript and see what descriptions are generated."""

import sys
sys.path.insert(0, "/Users/eugene/Documents/Github/XIVTimelineGenerator")

from agents.youtube_guide_agent import YouTubeGuideDiscoveryAgent
from agents.transcript_enrichment_orchestrator import TranscriptEnrichmentOrchestrator

VIDEO_ID = "w1uuwzhyf5A"

print(f"Fetching transcript for video: {VIDEO_ID}")
print("=" * 60)

guide_agent = YouTubeGuideDiscoveryAgent(api_key=None)

try:
    transcript = guide_agent.get_transcript_only(VIDEO_ID)
    
    if transcript:
        print(f"\nGot transcript!")
        print(f"  Title: {transcript.video_metadata.title}")
        print(f"  Channel: {transcript.video_metadata.channel}")
        print(f"  Segments: {len(transcript.segments)}")
        
        print("\n" + "=" * 60)
        print("Searching transcript for M11S mechanic keywords...")
        print("=" * 60)
        
        search_terms = [
            "tank buster", "raidwide", "stack", "spread", "cleave",
            "dark", "force", "soul", "rush", "slash", "dimension",
            "mirage", "akh", "afah", "triple", "tyrant", "sword", 
            "cone", "frontal", "aoe", "knockback", "tether", "orbit", "scythe",
        ]
        
        for term in search_terms:
            matches = []
            for seg in transcript.segments:
                if term.lower() in seg.text.lower():
                    matches.append(seg.text)
            
            if matches:
                print(f"\n'{term}': {len(matches)} matches")
                for m in matches[:3]:
                    print(f"  - {m[:80]}...")
        
        print("\n" + "=" * 60)
        print("Testing description generation with snippet matching...")
        print("=" * 60)
        
        orchestrator = TranscriptEnrichmentOrchestrator(
            llm_client=None,
            youtube_api_key=None,
        )
        
        test_abilities = [
            "Dark Force",
            "Soul Rush", 
            "Dimension Slash",
            "Akh Afah",
            "Triple Slash",
            "Scythe",
        ]
        
        print("\nGenerating descriptions:")
        for ability in test_abilities:
            snippets = orchestrator._find_transcript_snippets(ability, [transcript])
            
            if snippets:
                print(f"\n{ability}:")
                print(f"  Snippets: {len(snippets)}")
                for snip in snippets[:3]:
                    print(f"    - {snip[:120]}...")
                
                desc = orchestrator._rule_based_description(
                    ability,
                    {"type": "magical" if "Raidwide" in ability else "physical"}
                )
                print(f"  Generated: {desc}")
            else:
                print(f"\n{ability}: No snippets - trying fuzzy match...")
                
                ability_lower = ability.lower()
                for seg in transcript.segments:
                    seg_lower = seg.text.lower()
                    for word in ability_lower.split():
                        if len(word) > 3 and word in seg_lower:
                            print(f"  Found '{word}' in: {seg.text[:80]}...")
                            break
        
        orchestrator.close()
        guide_agent.close()
        
    else:
        print("No transcript found")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
