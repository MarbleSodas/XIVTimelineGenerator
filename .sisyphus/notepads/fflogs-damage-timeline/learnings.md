# FFLogs Damage Timeline Learnings

## Created fflogs_damage_timeline package

### Key patterns established:
- OAuth2 client credentials flow using requests library (not fflogsapi)
- Token stored in-memory in `self._token` instance variable
- Pagination handled via `nextPageTimestamp` loop in `fetch_events()`
- GraphQL queries defined as module-level constants
- Error handling via `response.raise_for_status()` and GraphQL errors array

### GraphQL endpoints used:
- API: `https://www.fflogs.com/api/v2/client`
- Token: `https://www.fflogs.com/oauth/token`

### Environment variables:
- FFLOGS_CLIENT_ID
- FFLOGS_CLIENT_SECRET

### Methods:
- `fetch_reports(zone_id, encounter_id)` - returns list of report dicts
- `fetch_fights(report_code, encounter_id)` - returns list of fight dicts
- `fetch_events(report_code, fight_id, start_time, end_time)` - returns merged paginated events

### Type narrowing fix:
- When assigning `self._token = data['access_token']`, pyright doesn't narrow the type
- Solution: Use local variable first, then assign to instance variable

## Timestamp Normalization (created normalizer.py)
- FF Logs timestamps are Unix milliseconds
- normalize_timestamps uses dict spread `{**event, "timestamp": ...}` to create new dicts
- This preserves the original events list completely unchanged
    - Verified: original events not mutated, new list returned

## Event Filters (created filters.py)
- `filter_hit_success(event)` - returns False for hitType=1 (miss), True otherwise
- `filter_non_auto_attack(event)` - returns False for abilityGameID < 100 (auto-attacks)
- `filter_player_targets(event, actors)` - checks actors dict for target's subType == "Player"
- `filter_damage_events(events, actors)` - combines all filters, returns new list (doesn't mutate)

### Constants:
- `AUTO_ATTACK_THRESHOLD = 100` - abilityGameID below this is auto-attack
- `HIT_TYPE_MISS = 1` - hitType == 1 means the attack missed

### Event structure:
- hitType: 1=miss, 2=hit, 4=crit, 6=overkill
- abilityGameID: FFXIV auto-attacks have low IDs (typically 1-99)


## CLI Entry Point (created cli.py, __main__.py)

### Files created:
- `src/fflogs_damage_timeline/cli.py` - Main CLI logic with argparse
- `src/fflogs_damage_timeline/__main__.py` - Package entry point

### CLI arguments:
- `--encounter` (required) - Encounter code like M11S, TOP, DSR
- `--limit` (default: 30) - Number of kill reports to fetch
- `--output-dir` (default: output/) - Output directory

### Encounter loading:
- Uses `fflogs.encounters.EncounterLoader` from existing code
- `loader.get_by_code(code)` returns `Encounter` dataclass or None
- Encounter config includes: code, full_name, boss_name, zone_id, encounter_id, expansion, category

### Error handling pattern:
- Per-fight error handling with `continue` (don't abort entire run)
- Each step (fetch fights, fetch events, process, write) wrapped in try/except
- Error count tracked and logged at end
- Returns exit code 1 if any fights failed

### Output path pattern:
- `{output_dir}/{encounter_code}/{report_code}-fight-{fight_id}.json`
- Skips existing files (checks with `output_path.exists()`)

### Type casting:
- `filter_damage_events` expects `list[Event]` but `fetch_events` returns `list[dict[str, Any]]`
- Solution: Use `cast(list[Event], events)` from typing

## Integration Tests (created test_integration.py tests)

### Test structure:
- `TestFilters` - tests filter functions with mock events and actors
- `TestNormalizer` - tests timestamp normalization
- `TestOutput` - tests JSON output with temp directory
- `TestFullPipeline` - end-to-end test with mocked GraphQL client

### Mock data patterns:
- Mock events use realistic FFXIV event structure (timestamp, targetID, sourceID, abilityGameID, hitType, amount)
- Mock actors dict keyed by actor ID for target/actor lookups
- MagicMock for GraphQL client methods returning test data

### Key test scenarios covered:
1. Filter removes auto-attacks (abilityGameID < 100)
2. Filter removes misses (hitType == 1)
3. Filter removes non-player targets
4. Normalizer subtracts fight_start_time correctly
5. Normalizer doesn't mutate original events
6. Output creates correct JSON structure
7. Output creates directory if not exists
8. Output skips existing files
9. Full pipeline with mocked GraphQL client
