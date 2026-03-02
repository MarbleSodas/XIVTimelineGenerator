#!/usr/bin/env python3
"""
Test script for CactbotTimelineAgent (non-atomic - simple HTTP + regex)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.cactbot_schemas import CactbotTimelineInput
from agents.cactbot_agent import CactbotTimelineAgent


def test_cactbot_agent():
    agent = CactbotTimelineAgent()
    
    test_cases = [
        {
            "name": "R7S - Brute Abombinator",
            "input": CactbotTimelineInput(
                boss_id="r7s",
                timeline_path="ui/raidboss/data/07-dt/raid/r7s.txt",
            ),
        },
    ]
    
    print("=" * 60)
    print("Testing CactbotTimelineAgent (non-atomic)")
    print("=" * 60)
    
    for test in test_cases:
        print(f"\n>>> Testing: {test['name']}")
        print(f"    Timeline path: {test['input'].timeline_path}")
        
        result = agent.run(test['input'])
        
        if result.fetch_success:
            print(f"    Success! Fetched {result.entry_count} timeline entries")
            
            print("\n    First 10 entries:")
            for entry in result.timeline_entries[:10]:
                print(f"      {entry.time:6.1f}s - {entry.name}")
            
            if len(result.timeline_entries) > 10:
                print(f"      ... and {len(result.timeline_entries) - 10} more entries")
        else:
            print(f"    Failed: {result.error_message}")
    
    agent.close()
    print("\n" + "=" * 60)
    print("Tests complete!")


if __name__ == "__main__":
    test_cactbot_agent()
