#!/usr/bin/env python3
"""
Direct test for CactbotTimelineAgent (non-atomic - simple HTTP + regex)
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from agents.cactbot_agent import CactbotTimelineAgent
from schemas.cactbot_schemas import CactbotTimelineInput


def test_cactbot_agent():
    agent = CactbotTimelineAgent()
    
    test_cases = [
        {"name": "R1S - Black Cat", "path": "ui/raidboss/data/07-dt/raid/r1s.txt"},
        {"name": "R2S - Honey B. Lovely", "path": "ui/raidboss/data/07-dt/raid/r2s.txt"},
        {"name": "R7S - Brute Abombinator", "path": "ui/raidboss/data/07-dt/raid/r7s.txt"},
    ]
    
    print("=" * 60)
    print("Testing CactbotTimelineAgent (non-atomic)")
    print("=" * 60)
    
    for test in test_cases:
        input_data = CactbotTimelineInput(boss_id=test["name"], timeline_path=test["path"])
        print(f"\n>>> Testing: {test['name']}")
        
        result = agent.run(input_data)
        
        if result.fetch_success:
            print(f"    Success! Fetched {result.entry_count} entries")
            for entry in result.timeline_entries[:5]:
                print(f"      {entry.time:6.1f}s - {entry.name}")
        else:
            print(f"    Failed: {result.error_message}")
    
    agent.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_cactbot_agent()
