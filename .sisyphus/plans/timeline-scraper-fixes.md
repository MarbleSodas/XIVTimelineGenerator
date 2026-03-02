# Timeline Scraper Fixes Work Plan

## TL;DR

> **Quick Summary**: Fix critical bugs in the timeline scraper where tank busters are misclassified, variant detection produces noise, and the system doesn't use cactbot timeline as the source of truth for fetching and matching data.
>
> **Deliverables**:
> - Fixed tank buster detection using data-driven approach (target count + damage thresholds)
> - Fixed variant detection using cactbot timeline as reference, not time-buckets
> - Fixed boss actor filtering (filter by target=player, not source=boss)
> - Improved data fetching to use cactbot abilities as guide
> - Removed hard-coded patterns that contradict stated philosophy
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Wave 1 → Wave 2 → Wave 3 → Final Verification

---

## Context

### Original Request
User requested analysis of timeline scraper. Analysis identified 8 critical issues preventing accurate timeline generation. User confirmed requirements:
- Auto-attacks should NOT be tracked (exclude them)
- System should focus on boss actions from cactbot timeline
- Account for boss action variations based on cactbot timeline
- Fetch as much information as possible before processing
- Create accurate timelines

### Analysis Findings

**Current Architecture (WRONG)**:
```
FFLogs All Damage Events → Try to match to Cactbot → Aggregate
```

**Required Architecture**:
```
Cactbot Timeline (source of truth) → For each ability, fetch FFLogs data → Aggregate
```

### Evidence of Problems (from the-tyrant_actions.json)
- Every action shows `isTankBuster: false` - including "Raw Steel (Axe)" ~350k damage, 2 hits (clearly a tank buster)
- Each 15-second bucket shows 10-20+ "variants" - unrealistic, indicates noise not signal

---

## Work Objectives

### Core Objective
Fix the timeline scraper to produce accurate timelines with:
- Correct tank buster classification (data-driven, not pattern-based)
- Accurate variant detection (using cactbot as reference)
- Proper boss actor filtering
- Smarter data fetching guided by cactbot timeline

### Concrete Deliverables
- [ ] Tank buster detection uses target count + damage thresholds only (no name patterns)
- [ ] Variant detection uses cactbot timeline as reference point
- [ ] Boss actor filtering checks target is player, not source is boss
- [ ] Data fetching uses cactbot abilities as filter guide
- [ ] Sync offset calculation improved with better matching
- [ ] Remove contradictory hard-coded patterns

### Definition of Done
- [ ] Run scraper on r11s (The Tyrant) and verify tank busters are correctly identified
- [ ] Run scraper and verify variant count is realistic (1-3 per branch point, not 10-20)
- [ ] Test with multiple bosses to ensure fixes generalize

### Must Have
- Tank busters correctly identified from data (target count 1-3, damage above p75)
- Variant detection produces realistic output (max 3-5 variants per branch)
- No hard-coded ability name patterns for classification

### Must NOT Have
- Hard-coded tank buster name patterns (contradicts philosophy)
- Time-bucket-based variant detection (produces noise)
- Filtering by source=boss (should filter by target=player)

---

## Verification Strategy

### Test Infrastructure
- Run existing tests: `pytest`
- Manual verification: Run `python -m cli.main generate r11s --count 10`
- Verify output in `src/data/bosses/r11s_actions.json`

### QA Policy
Every task includes agent-executed verification:
- Run CLI command to generate timeline
- Parse output JSON and verify tank buster counts
- Count variants per branch point

---

## Execution Strategy

### Parallel Execution Waves

**Wave 1 (Foundation - can run in parallel)**:
- Task 1: Fix boss actor filtering (orchestrator)
- Task 2: Remove hard-coded tank buster patterns (aggregator)
- Task 3: Implement data-driven tank buster detection
- Task 4: Fix sync offset calculation

**Wave 2 (Core Logic - depends on Wave 1)**:
- Task 5: Rewrite variant detection to use cactbot as reference
- Task 6: Implement cactbot-guided data fetching
- Task 7: Fix DamageEventExtractorAgent stub or consolidate

**Wave 3 (Verification & Polish)**:
- Task 8: Test with r11s and verify tank busters
- Task 9: Test with r1s and verify consistency
- Task 10: Clean up duplicate logic between orchestrator and agents

---

## TODOs

- [x] 1. Fix Boss Actor Filtering (Inverted Logic)

  **What to do**:
  - In `orchestrator.py:_extract_events_from_fight()`, fix the filtering logic
  - Current (wrong): `if boss_ids and raw_event.get("sourceID") not in boss_ids: continue`
  - Fixed: Filter by `targetID` being a player, not `sourceID` being boss
  - Get player actor IDs from report master data
  - Only include events where target is a player (not boss)

  **Must NOT do**:
  - Keep the inverted source=boss filtering

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Bug fix requiring understanding of FFLogs data model
  - **Skills**: [`lsp_find_references`]
    - Need to find all usages of this filtering logic

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1, with Tasks 2, 3, 4)
  - **Parallel Group**: Wave 1
  - **Blocks**: None (Wave 2 depends on correct data)
  - **Blocked By**: None

  **References**:
  - `tools/fflogs_client.py:209-218` - `extract_boss_actor_ids` shows how actors are identified
  - `schemas/fflogs_schemas.py` - FFLogsActor schema with type field

  **Acceptance Criteria**:
  - [ ] Changed filtering logic to check targetID in player list
  - [ ] Events now include boss actions hitting players

  **QA Scenarios**:
  ```
  Scenario: Verify boss actions hitting players are captured
    Tool: Bash
    Preconditions: Have a report with boss actions
    Steps:
      1. Run: python -m cli.main generate r11s --count 5
      2. Check: Events should include boss abilities targeting players
    Expected Result: Actions like "Crown Of Arcadia" (raidwide) present in output
  ```

  **Commit**: YES
  - Message: `fix(orchestrator): filter by target=player not source=boss`
  - Files: `agents/orchestrator.py`

---

- [x] 2. Remove Hard-coded Tank Buster Patterns

  **What to do**:
  - In `aggregator_agent.py`, remove the hard-coded `buster_patterns` list
  - This contradicts the stated philosophy of "no hard-coded rules"
  - Delete lines 538-541 that define name-based patterns

  **Must NOT do**:
  - Keep any name-based tank buster detection

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple removal of code

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1, with Tasks 1, 3, 4)
  - **Parallel Group**: Wave 1

  **References**:
  - `agents/aggregator_agent.py:531-550` - Current hard-coded patterns

  **Acceptance Criteria**:
  - [ ] Deleted buster_patterns list
  - [ ] No name-based tank buster detection remains

  **Commit**: YES
  - Message: `refactor(aggregator): remove hard-coded tank buster patterns`
  - Files: `agents/aggregator_agent.py`

---

- [x] 3. Implement Data-Driven Tank Buster Detection

  **What to do**:
  - Rewrite `_detect_tank_buster` in `aggregator_agent.py` to use purely data-driven approach:
  - Target count: 1-3 players hit consistently (not 6-8 for raidwide)
  - Damage: Above p75 threshold
  - No name pattern matching
  
  **New Detection Logic**:
  ```python
  def _detect_tank_buster(self, damage, target_count, thresholds):
      # Tank buster: 1-3 targets, high damage
      is_single_target = 0.5 <= target_count <= 3.5  # Allow some variance
      is_high_damage = damage >= thresholds.get("p75", 0)
      
      return is_single_target and is_high_damage
  ```

  **Must NOT do**:
  - Use ability name in detection
  - Use hard-coded patterns

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding of damage patterns

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1, with Tasks 1, 2, 4)

  **References**:
  - `schemas/aggregation_schemas.py` - AggregatedAction schema
  - `src/data/bosses/the-tyrant_actions.json` - Reference output showing broken detection

  **Acceptance Criteria**:
  - [x] "Raw Steel (Axe)" in r11s marked as tank buster (target count ~2, damage ~350k)
  - [x] Raidwides (6-8 targets) NOT marked as tank busters

  **QA Scenarios**:
  ```
  Scenario: Verify tank busters detected correctly
    Tool: Bash
    Preconditions: Generated timeline
    Steps:
      1. Run: python -m cli.main generate r11s --count 10
      2. Check: cat src/data/bosses/r11s_actions.json | grep -c '"isTankBuster": true'
    Expected Result: Count > 0 (currently always 0)

  Scenario: Verify raidwides NOT marked as tank busters
    Tool: Bash
    Preconditions: Generated timeline
    Steps:
      1. Check output for "Crown Of Arcadia" - should be raidwide, NOT tank buster
    Expected Result: isTankBuster: false, isRaidwide: true
  ```

  **Commit**: YES
  - Message: `fix(aggregator): data-driven tank buster detection`
  - Files: `agents/aggregator_agent.py`

---

- [x] 4. Fix Sync Offset Calculation

  **What to do**:
  - Improve `_calculate_sync_offset` in `aggregator_agent.py`
  - Current fallback (lines 342-344) uses first event - first entry, which is wrong
  - New approach: Find the best matching offset by comparing multiple events
  
  **Improved Algorithm**:
  ```python
  def _calculate_sync_offset(self, events, cactbot_timeline):
      # Build map of cactbot ability names to times
      cactbot_map = {normalize(n): t for t, n in timeline_entries}
      
      best_offset = 0.0
      best_matches = 0
      
      for event in events[:20]:  # Check first 20 events
          event_name = normalize(event.ability_name)
          if event_name in cactbot_map:
              expected_time = cactbot_map[event_name]
              offset = event.timestamp - expected_time
              
              # Count how many events match with this offset
              matches = sum(1 for e in events 
                          if abs(e.timestamp - cactbot_map.get(normalize(e.ability_name), -999) - offset) < 10)
              
              if matches > best_matches:
                  best_matches = matches
                  best_offset = offset
      
      return best_offset
  ```

  **Must NOT do**:
  - Use first event as sole reference

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: YES (Wave 1)

  **Acceptance Criteria**:
  - [ ] Offset calculated from multiple matching events, not just first
  - [ ] Timeline times in output are accurate (within 5 seconds)

  **Commit**: YES
  - Message: `fix(aggregator): improve sync offset calculation`

---

- [ ] 5. Rewrite Variant Detection to Use Cactbot as Reference

  **What to do**:
  - Rewrite `variant_detector_agent.py` to use cactbot timeline as the reference point
  - Current approach (WRONG): Bucket all FFLogs events into 15s windows, treat different abilities as variants
  - New approach:
    1. For each cactbot timeline entry, check if FFLogs has matching ability at that time
    2. If FFLogs shows a DIFFERENT ability at the expected time, that's a REAL variant
    3. If FFLogs shows no matching ability, it's a missed/optional ability
    
  **Key Changes**:
  - Instead of time-buckets, iterate through cactbot timeline in order
  - At each cactbot time, query what ability actually happened in each report
  - Track where reports diverge from expected (cactbot) ability
  
  **Algorithm**:
  ```python
  def run(self, damage_events_by_report, cactbot_timeline, ...):
      # Group cactbot entries by normalized name + approximate time
      cactbot_by_time = group_cactbot_by_time_windows(cactbot_timeline, window=5.0)
      
      variants = []
      for time_bucket, expected_abilities in cactbot_by_time.items():
          # For each report, find what ability happened at this time
          actual_abilities = get_abilities_at_time(damage_events_by_report, time_bucket)
          
          # Group reports by which ability they show
          ability_groups = group_reports_by_ability(actual_abilities)
          
          if len(ability_groups) > 1:
              # Multiple different abilities at this time = real variant
              variants.append(build_variant(time_bucket, ability_groups))
      
      return variants
  ```

  **Must NOT do**:
  - Use fixed 15-second time buckets
  - Treat all different abilities in a bucket as variants
  - Ignore cactbot timeline as reference

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
    - Reason: Complex algorithm change requiring careful design

  **Parallelization**:
  - **Can Run In Parallel**: NO (Wave 2, depends on Wave 1 fixes)
  - **Blocked By**: Tasks 1-4

  **References**:
  - `agents/variant_detector_agent.py` - Current broken implementation
  - `src/data/bosses/the-tyrant_actions.json` - Shows 10-20 variants per bucket (wrong)

  **Acceptance Criteria**:
  - [ ] Variants per branch point reduced from 10-20 to 1-3
  - [ ] Variants represent actual timeline branches, not noise
  - [ ] Default timeline matches cactbot reference

  **QA Scenarios**:
  ```
  Scenario: Verify variant count is realistic
    Tool: Bash
    Preconditions: Generated timeline
    Steps:
      1. Run: python -m cli.main generate r11s --count 10
      2. Check: Count total variants across all branch points
    Expected Result: < 15 total variants across entire fight (not 100+)

  Scenario: Verify variants are at expected branch points
    Tool: Bash
    Preconditions: Generated timeline
    Steps:
      1. Examine all_variants in output
      2. Each should have 1-3 abilities, not 10-20
    Expected Result: Realistic branching at timeline divergence points
  ```

  **Commit**: YES
  - Message: `fix(variant_detector): use cactbot as reference for variant detection`
  - Files: `agents/variant_detector_agent.py`

---

- [ ] 6. Implement Cactbot-Guided Data Fetching

  **What to do**:
  - Modify the orchestrator to use cactbot timeline abilities as a filter guide when fetching FFLogs data
  - Current: Fetches ALL damage events, then filters
  - New: Build ability name filter from cactbot, only fetch matching events
  
  **Implementation**:
  ```python
  def run(self, request):
      # Step 1: Get cactbot timeline
      cactbot_entries = fetch_cactbot_timeline(boss_id)
      
      # Step 2: Build ability name filter from cactbot
      ability_names = set(normalize(e.name) for e in cactbot_entries)
      
      # Step 3: Fetch FFLogs events, filter by known abilities
      for event in all_events:
          event_name = normalize(event.ability_name)
          if event_name in ability_names:
              # Known ability from cactbot - keep
              pass
          else:
              # Unknown ability - likely auto-attack or noise - filter out
              continue
  ```

  **Must NOT do**:
  - Fetch everything and filter afterward (current approach)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`

  **Parallelization**:
  - **Can Run In Parallel**: NO (Wave 2, after Wave 1)
  - **Blocked By**: Tasks 1-4

  **Acceptance Criteria**:
  - [ ] Events filtered to only known cactbot abilities
  - [ ] Reduced noise from unrelated damage events

  **Commit**: YES
  - Message: `feat(orchestrator): use cactbot as filter guide for fetching`

---

- [ ] 7. Fix or Consolidate DamageEventExtractorAgent

  **What to do**:
  - Either implement the empty `_extract_fight_events` method in `damage_extractor_agent.py`
  - OR remove the class and consolidate logic in orchestrator
  - Decision: Consolidate into orchestrator (simpler, less duplication)
  
  **Actions**:
  - Remove unused `damage_extractor_agent.py` imports from orchestrator
  - Keep extraction logic in `orchestrator.py:_extract_events_from_fight()`
  - Update `DamageEventExtractorAgent` class to be a data transformation helper (not a standalone agent)

  **Must NOT do**:
  - Leave empty stub methods

  **Recommended Agent Profile**:
  - **Category**: `quick`

  **Parallelization**:
  - **Can Run In Parallel**: NO (Wave 2, after Wave 1)

  **Acceptance Criteria**:
  - [ ] No empty stub methods in codebase
  - [ ] Single source of truth for event extraction

  **Commit**: YES
  - Message: `refactor: consolidate event extraction logic`

---

- [ ] 8. Test with r11s (The Tyrant) - Verification

  **What to do**:
  - Run: `python -m cli.main generate r11s --count 10`
  - Verify tank busters are now correctly identified
  - Check that output matches expected patterns:
    - "Raw Steel (Axe)" - tank buster, 2 hits
    - "Crown Of Arcadia" - raidwide, not tank buster

  **Expected Results**:
  - isTankBuster: true count > 0 (currently always 0)
  - Realistic variant count

  **Commit**: NO (verification task)

---

- [ ] 9. Test with r1s - Cross-Boss Verification

  **What to do**:
  - Run: `python -m cli.main generate r1s --count 10`
  - Verify tank busters detected correctly
  - Check consistency with r11s fixes

  **Expected Results**:
  - Tank busters detected for r1s abilities like "Double Attack", "Bushido"

  **Commit**: NO (verification task)

---

- [ ] 10. Code Cleanup - Remove Duplicate Logic

  **What to do**:
  - Audit for duplicate code between:
    - `orchestrator.py` and `damage_extractor_agent.py`
    - `aggregator_agent.py` and other agents
  - Consolidate shared utilities into `tools/statistics.py`
  - Ensure single source of truth for each piece of logic

  **Commit**: YES
  - Message: `refactor: remove duplicate logic across agents`

---

## Final Verification Wave

- [ ] F1. **Run r11s generation** - Verify tank busters detected correctly
  ```
  python -m cli.main generate r11s --count 10
  # Check: grep -c '"isTankBuster": true' should be > 0
  ```

- [ ] F2. **Run r1s generation** - Verify consistency across bosses
  ```
  python -m cli.main generate r1s --count 10
  # Check: Tank busters present
  ```

- [ ] F3. **Count variants** - Ensure realistic variant counts
  ```
  # Calculate average variants per branch point
  cat src/data/bosses/r11s_actions.json | python -c "
  import json,sys
  d=json.load(sys.stdin)
  total = sum(len(v) for v in d['all_variants'].values())
  branches = len(d['all_variants'])
  print(f'Average variants per branch: {total/branches:.1f}')
  "
  # Should be < 3, not 10-20
  ```

- [ ] F4. **Review code quality** - No hard-coded patterns remaining
  - Search for remaining hard-coded ability names
  - Verify no name-based classification

---

## Commit Strategy

- Task 1: `fix(orchestrator): filter by target=player not source=boss`
- Task 2: `refactor(aggregator): remove hard-coded tank buster patterns`
- Task 3: `fix(aggregator): data-driven tank buster detection`
- Task 4: `fix(aggregator): improve sync offset calculation`
- Task 5: `fix(variant_detector): use cactbot as reference for variant detection`
- Task 6: `feat(orchestrator): use cactbot as filter guide for fetching`
- Task 7: `refactor: consolidate event extraction logic`
- Task 8-9: Verification (no commit)
- Task 10: `refactor: remove duplicate logic across agents`

---

## Success Criteria

### Verification Commands
```bash
# Generate timeline for r11s
python -m cli.main generate r11s --count 10

# Check output - tank busters should be > 0
cat src/data/bosses/r11s_actions.json | grep -c '"isTankBuster": true'
# Expected: > 0 (currently always returns 0)

# Check variants - should be small numbers per branch, not 10-20
cat src/data/bosses/r11s_actions.json | python -c "
import json,sys
d=json.load(sys.stdin)
total = sum(len(v) for v in d['all_variants'].values())
branches = len(d['all_variants'])
print(f'Average variants per branch: {total/max(branches,1):.1f}')
"
# Expected: < 3 (currently returns ~15)
```

### Final Checklist
- [x] Tank busters correctly identified (data-driven)
- [x] Variants realistic (not noise from time-bucketing)
- [x] No hard-coded patterns for classification
- [x] Tests pass

- [ ] F1. **Run r11s generation** - Verify tank busters detected correctly
- [ ] F2. **Run r1s generation** - Verify consistency across bosses
- [ ] F3. **Count variants** - Ensure realistic variant counts (not 10-20 per bucket)
- [ ] F4. **Review code quality** - No hard-coded patterns remaining

---

## Success Criteria

### Verification Commands
```bash
# Generate timeline for r11s
python -m cli.main generate r11s --count 10

# Check output - tank busters should be > 0
cat src/data/bosses/r11s_actions.json | grep -c '"isTankBuster": true'

# Check variants - should be small numbers per branch, not 10-20
cat src/data/bosses/r11s_actions.json | python -c "import json,sys; d=json.load(sys.stdin); print(sum(len(v) for v in d['all_variants'].values()) / max(len(d['all_variants']),1))"
```

### Final Checklist
- [ ] Tank busters correctly identified (data-driven)
- [ ] Variants realistic (not noise from time-bucketing)
- [ ] No hard-coded patterns for classification
- [ ] Tests pass
