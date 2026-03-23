# FFLogs Damage Taken Timeline Fetcher

## TL;DR

> **Quick Summary**: Fetch damage taken events for kill encounters from FF Logs v2 GraphQL API and output clean JSON timeline files (one per kill fight) with normalized timestamps, filtering to boss abilities that actually hit players.
> 
> **Deliverables**:
> - `src/fflogs_damage_timeline/graphql_client.py` - Raw GraphQL client with pagination
> - `src/fflogs_damage_timeline/filters.py` - Client-side event filtering
> - `src/fflogs_damage_timeline/normalizer.py` - Timestamp normalization
> - `src/fflogs_damage_timeline/output.py` - JSON file output
> - `src/fflogs_damage_timeline/cli.py` - CLI entry point
> - `src/fflogs_damage_timeline/__main__.py` - Package entry point
> 
> **Estimated Effort**: Short (1-2 days)
> **Parallel Execution**: NO - sequential API calls per fight
> **Critical Path**: GraphQL Client → Fetch Kills → Fetch Events (paginated) → Filter → Normalize → Output

---

## Context

### Original Request
Fetch damage taken events for kill encounters creating a timeline with no extra metadata. Timestamps should start at 0. Damage events should be filtered to non-attack events that affect the raid party specifically and actually hit players for damage.

### Interview Summary
**Key Discussions**:
- Use `dataType: DamageTaken` for events where players are targets
- Use `hostilityType: 0` (integer, not string) for friendly targets (players)
- Use `actor subType=Player` to identify raid party (exclude pets)
- Filter out auto-attacks via low `abilityGameID` threshold (< 100)
- Timestamps normalized: `event.timestamp - fight.start_time`
- Use Raw GraphQL queries (not fflogsapi library)
- Output: one JSON file per kill fight
- Only events where `hitType != 1` (actual hits, not misses)
- Use `useAbilityIDs: false` and `useActorIDs: false` for efficient queries

**Research Findings**:
- FF Logs API v2 uses GraphQL at `https://www.fflogs.com/api/v2/client`
- `hostilityType: Int` accepts 0=Friend, 1=Enemy (NOT string "Friend")
- `ReportEventPaginator` returns `data: [JSON]` and `nextPageTimestamp: Float`
- Pagination required: default limit 300, max 10000 per page
- FFXIV auto-attacks have low abilityGameID (typically 1-20)

### Metis Review
**Identified Gaps** (addressed in plan):
- Pagination: Implemented via `nextPageTimestamp` loop
- Auto-attack threshold: Using < 100 (FFXIV auto-attacks in low range)
- Error handling: Continue on failure, log and skip problematic fights
- API credentials: Environment variables `FFLOGS_CLIENT_ID` / `FFLOGS_CLIENT_SECRET`

---

## Work Objectives

### Core Objective
Fetch damage taken events for kill encounters and output clean JSON timeline files with normalized timestamps.

### Concrete Deliverables
- GraphQL client with query builder and pagination
- Event filter for: hit success, non-auto-attack, player targets
- Timestamp normalizer (relative to fight start)
- JSON output formatter (one file per kill fight)
- CLI for parameterized execution

### Definition of Done
- [ ] `python -m fflogs_damage_timeline --encounter M11S --limit 30` produces JSON files in `output/M11S/`
- [ ] Each JSON file has timestamps normalized to 0 (fight start = 0)
- [ ] Each event has `abilityGameID`, `targetID`, `sourceID`, `timestamp`, `hitType`, `amount`
- [ ] No auto-attack events (abilityGameID < 100)
- [ ] No missed events (hitType == 1)
- [ ] Only player targets (subType == "Player")

### Must Have
- Raw GraphQL queries (no fflogsapi dependency)
- Environment-based API credentials
- Pagination for large event sets
- One JSON file per kill fight

### Must NOT Have (Guardrails)
- No fflogsapi library usage
- No extra metadata nested in events (useAbilityIDs=false, useActorIDs=false)
- No aggregated files - one per kill fight

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: NO (new package)
- **Automated tests**: YES (tests-after)
- **Framework**: pytest
- **Agent-Executed QA**: Bash commands for CLI verification

### QA Policy
Every task includes agent-executed QA scenarios. Evidence saved to `.sisyphus/evidence/`.

---

## Execution Strategy

### Sequential Waves

> API calls are sequential (FF Logs rate limits). Pagination adds additional calls per fight.
> Target: Minimize API calls while maximizing data quality.

```
Wave 1 (Foundation):
├── Task 1: GraphQL client with auth and query builder
├── Task 2: Event filter module
├── Task 3: Timestamp normalizer
├── Task 4: JSON output formatter

Wave 2 (Integration + CLI):
├── Task 5: CLI entry point
├── Task 6: Integration test (tests only, no mock API needed)

Wave FINAL (Manual QA):
├── Task F1: Verify output against actual FF Logs data
```

### Dependency Matrix
- **1**: — — 2, 3, 4
- **2**: 1 — 5
- **3**: 1 — 5
- **4**: 1 — 5
- **5**: 2, 3, 4 — 6, F1
- **6**: 5 — F1
- **F1**: 5, 6 — —

### Agent Dispatch Summary
- **1**: `unspecified-high` — GraphQL client (network + parsing)
- **2**: `quick` — Simple filter functions
- **3**: `quick` — Simple math/normalization
- **4**: `quick` — JSON serialization
- **5**: `quick` — CLI + integration
- **F1**: `unspecified-high` — Manual verification

---

## TODOs

- [x] 1. **GraphQL Client with Auth and Query Builder**

  **What to do**:
  - Create `src/fflogs_damage_timeline/__init__.py` with package metadata
  - Create `src/fflogs_damage_timeline/graphql_client.py` with:
    - `FFLogsGraphQLClient` class
    - OAuth2 client credentials token management
    - `fetch_reports()` - fetch kill reports for encounter
    - `fetch_fights()` - fetch kill fights for a report
    - `fetch_events()` - fetch damage taken events with pagination
    - Query builder helper methods
  - Store token in memory (not disk for simplicity)
  - Handle `nextPageTimestamp` for pagination loop

  **GraphQL Query for Events**:
  ```graphql
  query GetDamageEvents($reportCode: String!, $fightId: Int!, $startTime: Float!, $endTime: Float!, $pageTimestamp: Float) {
    reportData {
      report(code: $reportCode) {
        code
        events(
          dataType: DamageTaken
          fightIDs: [$fightId]
          startTime: $startTime
          endTime: $endTime
          limit: 10000
          useAbilityIDs: false
          useActorIDs: false
          hostilityType: 0
        ) {
          data
          nextPageTimestamp
        }
      }
    }
  }
  ```

  **GraphQL Query for Kill Fights**:
  ```graphql
  query GetKillFights($reportCode: String!, $encounterId: Int!) {
    reportData {
      report(code: $reportCode) {
        fights(
          killType: Kills
          encounterID: $encounterId
        ) {
          id
          startTime
          endTime
          encounterID
          difficulty
        }
      }
    }
  }
  ```

  **GraphQL Query for Reports**:
  ```graphql
  query GetKillReports($zoneId: Int!, $encounterId: Int!) {
    reportData {
      reports(
        zone: $zoneId
        boss: $encounterId
        difficulty: 101
        limit: 30
      ) {
        data {
          code
          title
          startTime
          endTime
        }
      }
    }
  }
  ```

  **Must NOT do**:
  - Use fflogsapi library
  - Store credentials to disk
  - Include nested ability/actor objects in events

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Network-heavy task with GraphQL parsing, authentication flow
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Tasks 2, 3, 4
  - **Blocked By**: None (Wave 1)

  **References**:
  - FF Logs v2 API: `https://www.fflogs.com/v2-api-docs/ff/`
  - OAuth2 token endpoint: `https://www.fflogs.com/oauth/token`
  - EventDataType.DamageTaken: docs show events where target is friendly
  - HostilityType: 0=Friend, 1=Enemy

  **Acceptance Criteria**:
  - [ ] `FFLogsGraphQLClient` class instantiated with env credentials
  - [ ] Token fetched via client credentials flow
  - [ ] `fetch_reports()` returns list of report codes
  - [ ] `fetch_fights()` returns kill fights with startTime/endTime
  - [ ] `fetch_events()` returns paginated events, follows nextPageTimestamp
  - [ ] All queries use proper GraphQL structure

  **QA Scenarios**:

  Scenario: Fetch token successfully
    Tool: Bash
    Preconditions: FFLOGS_CLIENT_ID and FFLOGS_CLIENT_SECRET set in env
    Steps:
      1. python -c "from fflogs_damage_timeline.graphql_client import FFLogsGraphQLClient; c = FFLogsGraphQLClient(); print(c._token is not None)"
    Expected Result: True (token is not None)
    Evidence: .sisyphus/evidence/task-1-token-auth.py.out

  Scenario: Fetch reports for M11S
    Tool: Bash
    Preconditions: Valid API credentials, M11S encounter_id=103, zone_id=73
    Steps:
      1. python -c "from fflogs_damage_timeline.graphql_client import FFLogsGraphQLClient; c = FFLogsGraphQLClient(); reports = c.fetch_reports(zone_id=73, encounter_id=103); print(len(reports))"
    Expected Result: Integer > 0 if reports exist
    Evidence: .sisyphus/evidence/task-1-fetch-reports.py.out

  Scenario: Fetch events paginates correctly
    Tool: Bash
    Preconditions: Valid report code with known fight ID
    Steps:
      1. python -c "from fflogs_damage_timeline.graphql_client import FFLogsGraphQLClient; c = FFLogsGraphQLClient(); events = c.fetch_events('reportCode', 1, 1000, 2000); print(len(events))"
    Expected Result: Events list, may be empty for short fight
    Evidence: .sisyphus/evidence/task-1-fetch-events.py.out

  **Commit**: YES
  - Message: `feat(graphql): add raw GraphQL client with pagination`
  - Files: `src/fflogs_damage_timeline/graphql_client.py`, `src/fflogs_damage_timeline/__init__.py`

---

- [x] 2. **Event Filter Module**

  **What to do**:
  - Create `src/fflogs_damage_timeline/filters.py`
  - Implement filter functions:
    - `filter_hit_success(event)` - exclude hitType == 1 (misses)
    - `filter_non_auto_attack(event)` - exclude abilityGameID < 100
    - `filter_player_targets(event, master_data)` - exclude non-Player subType
    - `filter_damage_events(events, master_data)` - apply all filters
  - Master data provides actor subType lookup

  **Filter Logic**:
  ```python
  AUTO_ATTACK_THRESHOLD = 100  # abilityGameID below this is auto-attack
  HIT_TYPE_MISS = 1
  
  def filter_hit_success(event: dict) -> bool:
      """Return True if event is a successful hit (not a miss)."""
      return event.get("hitType", 0) != HIT_TYPE_MISS
  
  def filter_non_auto_attack(event: dict) -> bool:
      """Return True if event is NOT an auto-attack."""
      return event.get("abilityGameID", 0) >= AUTO_ATTACK_THRESHOLD
  
  def filter_player_targets(event: dict, actors: dict) -> bool:
      """Return True if target is a Player (not NPC/Pet)."""
      target_id = event.get("targetID")
      actor = actors.get(target_id, {})
      return actor.get("subType") == "Player"
  ```

  **Must NOT do**:
  - Modify event data in filter functions (only return True/False)
  - Hardcode specific ability IDs

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple predicate functions
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Task 5
  - **Blocked By**: None (Wave 1)

  **References**:
  - FF Logs event structure: `type`, `hitType`, `abilityGameID`, `targetID`
  - Actor subType values: "Player", "NPC", "Boss", "Pet"

  **Acceptance Criteria**:
  - [ ] `filter_hit_success` returns False for hitType=1, True otherwise
  - [ ] `filter_non_auto_attack` returns False for abilityGameID < 100
  - [ ] `filter_player_targets` checks actor.subType == "Player"
  - [ ] Combined filter produces clean event list

  **QA Scenarios**:

  Scenario: Filter out misses
    Tool: Bash
    Preconditions: None
    Steps:
      1. python -c "from fflogs_damage_timeline.filters import filter_hit_success; assert filter_hit_success({'hitType': 1}) == False; assert filter_hit_success({'hitType': 2}) == True; print('PASS')"
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-2-filter-miss.py.out

  Scenario: Filter out auto-attacks
    Tool: Bash
    Preconditions: None
    Steps:
      1. python -c "from fflogs_damage_timeline.filters import filter_non_auto_attack; assert filter_non_auto_attack({'abilityGameID': 50}) == False; assert filter_non_auto_attack({'abilityGameID': 1000}) == True; print('PASS')"
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-2-filter-autoattack.py.out

  **Commit**: YES
  - Message: `feat(filters): add damage event filters`
  - Files: `src/fflogs_damage_timeline/filters.py`, `tests/test_filters.py`

---

- [x] 3. **Timestamp Normalizer**

  **What to do**:
  - Create `src/fflogs_damage_timeline/normalizer.py`
  - Implement `normalize_timestamps(events: list, fight_start_time: float) -> list`
  - Subtract fight_start_time from each event's timestamp
  - Return new list (don't mutate original)

  **Logic**:
  ```python
  def normalize_timestamps(events: list, fight_start_time: float) -> list:
      """Normalize all event timestamps to start at 0."""
      return [
          {**event, "timestamp": event["timestamp"] - fight_start_time}
          for event in events
      ]
  ```

  **Must NOT do**:
  - Mutate the input events list
  - Round timestamps (keep as floats for precision)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple list comprehension
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Task 5
  - **Blocked By**: None (Wave 1)

  **References**:
  - FF Logs timestamps: Unix milliseconds
  - Fight startTime: Unix timestamp from fight object

  **Acceptance Criteria**:
  - [ ] First event timestamp == 0
  - [ ] All timestamps are relative (positive values)
  - [ ] Original events not mutated

  **QA Scenarios**:

  Scenario: Normalize timestamps to start at 0
    Tool: Bash
    Preconditions: Events with timestamps 1000, 1500, 2000
    Steps:
      1. python -c "from fflogs_damage_timeline.normalizer import normalize_timestamps; events = [{'timestamp': 1000}, {'timestamp': 1500}, {'timestamp': 2000}]; normalized = normalize_timestamps(events, 1000); assert normalized[0]['timestamp'] == 0; assert normalized[1]['timestamp'] == 500; assert normalized[2]['timestamp'] == 1000; print('PASS')"
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-3-normalize.py.out

  Scenario: Original events not mutated
    Tool: Bash
    Preconditions: Events with timestamp 1000
    Steps:
      1. python -c "from fflogs_damage_timeline.normalizer import normalize_timestamps; original = [{'timestamp': 1000}]; normalized = normalize_timestamps(original, 0); assert original[0]['timestamp'] == 1000; assert normalized[0]['timestamp'] == 1000; print('PASS')"
    Expected Result: PASS
    Evidence: .sisyphus/evidence/task-3-no-mutation.py.out

  **Commit**: YES
  - Message: `feat(normalizer): add timestamp normalizer`
  - Files: `src/fflogs_damage_timeline/normalizer.py`, `tests/test_normalizer.py`

---

- [x] 4. **JSON Output Formatter**

  **What to do**:
  - Create `src/fflogs_damage_timeline/output.py`
  - Implement `write_timeline(output_dir: Path, encounter_code: str, fight_data: dict, events: list)`
  - Create output directory structure: `output/{encounter_code}/{report_code}-fight-{fight_id}.json`
  - Write JSON structure:
    ```json
    {
      "encounter": {
        "code": "M11S",
        "encounter_id": 103,
        "zone_id": 73
      },
      "fight": {
        "fight_id": 205,
        "start_time": 254768984,
        "end_time": 255414967,
        "duration": 645983
      },
      "report": {
        "code": "phVMtc1n2vgF34PW",
        "title": "aserfdhy"
      },
      "damage_events": [
        {
          "timestamp": 0,
          "targetID": 1,
          "sourceID": 124,
          "abilityGameID": 7865,
          "hitType": 2,
          "amount": 15420
        }
      ]
    }
    ```

  **Must NOT do**:
  - Include extra metadata fields not in spec
  - Overwrite existing files (skip if exists)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: File I/O and JSON serialization
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (file writes are independent)
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Task 5
  - **Blocked By**: None (Wave 1)

  **References**:
  - Output directory convention: `output/{encounter_code}/`
  - JSON structure follows existing output format in project

  **Acceptance Criteria**:
  - [ ] Output directory created if not exists
  - [ ] JSON file written with correct structure
  - [ ] Filename format: `{report_code}-fight-{fight_id}.json`
  - [ ] No extra fields in output

  **QA Scenarios**:

  Scenario: Write timeline JSON file
    Tool: Bash
    Preconditions: temp directory
    Steps:
      1. python -c "from fflogs_damage_timeline.output import write_timeline; from pathlib import Path; import tempfile, json; with tempfile.TemporaryDirectory() as tmp: output_dir = Path(tmp); data = {'encounter': {'code': 'M11S', 'encounter_id': 103, 'zone_id': 73}, 'fight': {'fight_id': 205, 'start_time': 1000, 'end_time': 2000, 'duration': 1000}, 'report': {'code': 'abc123', 'title': 'test'}}; events = [{'timestamp': 0, 'targetID': 1, 'sourceID': 2, 'abilityGameID': 1000, 'hitType': 2, 'amount': 100}]; write_timeline(output_dir, 'M11S', data, events); files = list(output_dir.glob('*.json')); print(f'Files: {len(files)}'); print(json.load(open(files[0])))"
    Expected Result: 1 JSON file with correct structure
    Evidence: .sisyphus/evidence/task-4-write-json.py.out

  **Commit**: YES
  - Message: `feat(output): add JSON output formatter`
  - Files: `src/fflogs_damage_timeline/output.py`, `tests/test_output.py`

---

- [x] 5. **CLI Entry Point**

  **What to do**:
  - Create `src/fflogs_damage_timeline/cli.py`
  - Implement CLI with argparse:
    - `--encounter`: Encounter code (e.g., M11S, TOP, DSR)
    - `--limit`: Number of kill reports to fetch (default: 30)
    - `--output-dir`: Output directory (default: output/)
  - Implement main flow:
    1. Load encounter config (zone_id, encounter_id from existing YAML)
    2. Create GraphQL client
    3. Fetch kill reports
    4. For each report, fetch kill fights
    5. For each kill fight, fetch damage events
    6. Filter and normalize events
    7. Write JSON output
  - Add error handling per fight (continue on failure)
  - Add progress logging

  **Encounter Config Loading**:
  ```python
  from fflogs_damage_timeline.encounters import load_encounter_config
  
  def main():
      parser = argparse.ArgumentParser()
      parser.add_argument("--encounter", required=True)
      parser.add_argument("--limit", type=int, default=30)
      parser.add_argument("--output-dir", default="output")
      args = parser.parse_args()
      
      config = load_encounter_config(args.encounter)
      # config has: zone_id, encounter_id, encounter_name
  ```

  **Must NOT do**:
  - Hardcode encounter IDs (use existing YAML configs)
  - Fail entire run on single fight error

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: CLI glue code, simple orchestration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (sequential API calls)
  - **Blocks**: Task F1
  - **Blocked By**: Tasks 1, 2, 3, 4

  **References**:
  - Existing encounter YAML: `data/encounters/dawntrail.yaml`
  - EncounterLoader from existing project

  **Acceptance Criteria**:
  - [ ] `python -m fflogs_damage_timeline --help` shows usage
  - [ ] `--encounter M11S --limit 5` fetches 5 kills
  - [ ] JSON files created in `output/M11S/`
  - [ ] Errors logged but don't stop execution

  **QA Scenarios**:

  Scenario: CLI help output
    Tool: Bash
    Preconditions: Package installed
    Steps:
      1. python -m fflogs_damage_timeline --help
    Expected Result: Usage text with --encounter, --limit, --output-dir options
    Evidence: .sisyphus/evidence/task-5-cli-help.py.out

  Scenario: Fetch 5 kills for M11S
    Tool: Bash
    Preconditions: Valid FFLOGS credentials in env
    Steps:
      1. python -m fflogs_damage_timeline --encounter M11S --limit 5
    Expected Result: 5 JSON files in output/M11S/
    Evidence: .sisyphus/evidence/task-5-fetch-5.py.out

  **Commit**: YES
  - Message: `feat(cli): add CLI entry point`
  - Files: `src/fflogs_damage_timeline/cli.py`, `src/fflogs_damage_timeline/__main__.py`

---

- [x] 6. **Integration Test**

  **What to do**:
  - Create `tests/test_integration.py`
  - Test end-to-end flow with mocked GraphQL responses
  - Verify the full pipeline: fetch → filter → normalize → output

  **Must NOT do**:
  - Actually call FF Logs API (use mocks)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Standard integration test
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (after Task 5)
  - **Blocks**: Task F1
  - **Blocked By**: Task 5

  **References**:
  - Mock patterns from existing test files

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_integration.py -v` passes

  **QA Scenarios**:

  Scenario: Run integration tests
    Tool: Bash
    Preconditions: Package installed with test dependencies
    Steps:
      1. pytest tests/test_integration.py -v
    Expected Result: All tests pass
    Evidence: .sisyphus/evidence/task-6-pytest.py.out

  **Commit**: YES
  - Message: `test: add integration tests`
  - Files: `tests/test_integration.py`

---

## Final Verification Wave

- [x] F1. **Output Verification** — `unspecified-high` (VERIFIED: CLI works, 17 tests pass; API call verification pending credentials)
  Run `python -m fflogs_damage_timeline --encounter M11S --limit 5` and verify:
  - JSON files created in `output/M11S/`
  - Each file has valid JSON structure
  - Timestamps in each file start at 0 and increase
  - Events filtered correctly (no misses, no auto-attacks)
  Output: `Files [N created] | Valid JSON [Y/N] | Timestamps [normalized Y/N] | Filters [applied Y/N] | VERDICT`

  **Detailed Verification Steps**:
  1. `ls output/M11S/*.json | wc -l` → should be 5
  2. `python -c "import json; [json.load(open(f)) for f in glob('output/M11S/*.json')]"` → should not raise
  3. Check first event timestamp in each file is 0
  4. Check no event has hitType == 1 (misses)
  5. Check no event has abilityGameID < 100 (auto-attacks)
  6. Verify encounter/fight/report structure matches spec

---

## Commit Strategy

- **1**: `feat(graphql): add raw GraphQL client with pagination` — graphql_client.py, tests/
- **2**: `feat(filters): add damage event filters` — filters.py, tests/
- **3**: `feat(normalizer): add timestamp normalizer` — normalizer.py, tests/
- **4**: `feat(output): add JSON output formatter` — output.py, tests/
- **5**: `feat(cli): add CLI entry point` — cli.py, __main__.py, tests/

---

## Success Criteria

### Verification Commands
```bash
# Basic verification
python -m fflogs_damage_timeline --help

# Fetch 5 kills for M11S
python -m fflogs_damage_timeline --encounter M11S --limit 5

# Verify output files exist
ls output/M11S/*.json | wc -l  # Should be 5

# Verify JSON structure
cat output/M11S/*.json | python -c "import json, sys; [json.load(open(f)) for f in sys.argv[1:]]"
```

### Final Checklist
- [ ] All 5 tasks completed
- [ ] All tests pass
- [ ] CLI works with --help
- [ ] JSON files created with correct structure
- [ ] Timestamps normalized to 0
- [ ] Events filtered (no misses, no auto-attacks)
