# Draft: TUI Integration Analysis

## Current State
- TUI implemented in `main.py` using Rich library
- Two main TUI components:
  1. `TimelineGeneratorTUI` - Progress panel during generation
  2. `select_boss_interactive` - Interactive boss selection menu

## Issues Identified

### Critical
1. **Fake Progress (lines 438-439)**: Guide scraping marked "completed" without running
2. **Fake Research (lines 455-459)**: Targets step claims research but doesn't do any
3. **Code Duplication**: Success output printed twice (lines 488-512, 573-597)

### Minor
4. Unused imports: Layout, SpinnerColumn, TaskProgressColumn, Prompt
5. Single async call provides no real observability into agent work

## Recommendations

### Phase 1: Cleanup
- Remove unused imports
- Extract duplicated success output to shared function
- Fix misleading step names/messages

### Phase 2: Improve Transparency
- Show actual guide scraping status (or remove from steps if not applicable)
- Either show real agent progress or simplify the TUI to be honest about what it shows
- Add elapsed time display

### Phase 3: Usability
- Add keyboard hints for interactive mode
- Improve error display in TUI
- Add elapsed time to progress

## Test Strategy
- Run both interactive mode and --tui mode
- Verify all steps accurately reflect what's happening
- Check no errors in output
