# TUI Integration Cleanup and Improvement Plan

## TL;DR

> Clean up the TUI integration by removing misleading progress, fixing code duplication, and improving transparency.

> **Deliverables**:
> - Cleaned up main.py with fixed TUI
> - Removed misleading step messages
> - Extracted duplicated output code

> **Estimated Effort**: Short
> **Parallel Execution**: NO - sequential cleanup
> **Critical Path**: Remove unused imports → Fix duplicated code → Fix misleading steps → Test

---

## Context

### Original Request
Analyze the new TUI integration, cleanup anything that doesn't need to be there and improve the usability and transparency of the TUI making sure it is as clean as possible.

### Interview Summary
**Key Discussions**:
- User wants cleanup of unnecessary code
- User wants improved transparency (what's actually happening)
- User wants cleaner, more honest TUI

### Metis Review
**Identified Gaps** (addressed):
- Guide scraping steps are hardcoded as completed without running - FIX: either remove from steps or show real status
- Targets step claims research but doesn't actually do research - FIX: rename to be accurate
- Code duplication in success output printing - FIX: extract to shared function

---

## Work Objectives

### Core Objective
Clean up the TUI integration to be honest about what it's showing and remove code that doesn't need to be there.

### Concrete Deliverables
- main.py with cleaned up imports
- Fixed misleading step names/messages
- Extracted duplicated success output function
- Verified TUI works correctly

### Definition of Done
- [ ] No unused imports in main.py
- [ ] No misleading progress steps (fake "completed" without actual work)
- [ ] Duplicated code extracted to shared function
- [ ] Interactive mode works correctly
- [ ] TUI mode works correctly

### Must Have
- Working TUI and interactive mode
- Honest progress display (what's shown is actually happening)

### Must NOT Have
- Fake progress that misleads users
- Duplicate code blocks
- Unused imports

---

## Verification Strategy

> **Agent-Executed Verification** - Run the CLI to verify TUI works.

### Test Strategy
- **Infrastructure**: Not applicable (Python script)
- **Verification**: Run commands and verify output

### QA Scenarios

**Scenario: Interactive boss selection works**
  Tool: Bash
  Preconditions: None
  Steps:
    1. Run `cd /Users/eugene/Documents/Github/XIVTimelineGenerator && python3 run.py interactive --help` to verify command works
    2. (Cannot test interactive UI automatically - user to verify manually)
  Expected Result: Command executes without error

**Scenario: TUI mode shows correct progress**
  Tool: Bash
  Preconditions: None  
  Steps:
    1. Run `cd /Users/eugene/Documents/Github/XIVTimelineGenerator && python3 run.py generate p12s --tui` (may fail due to API key, but should show TUI)
    2. Check that TUI renders without errors
  Expected Result: TUI displays, no Python errors

---

## Execution Strategy

### Sequential Tasks

**Task 1**: Remove unused imports
- Remove: Layout, SpinnerColumn, TaskProgressColumn, Prompt (not used)

**Task 2**: Extract duplicated success output
- Create `_print_generation_success()` function
- Use in both `run_with_tui` and `run_cli`

**Task 3**: Fix misleading TUI steps
- Remove or fix fake "guide_icyveins" / "guide_hardcore" completed steps
- Rename "targets" step to accurately reflect what it does (or remove if not applicable)
- Make step messages honest about what's happening

**Task 4**: Test interactive and TUI modes
- Verify both modes work correctly

---

## TODOs

- [ ] 1. Remove unused Rich imports

  **What to do**:
  - Remove unused imports from main.py: Layout, SpinnerColumn, TaskProgressColumn, Prompt

  **Must NOT do**:
  - Remove imports that are actually used

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple import cleanup, single file change
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: None

  **References**:
  - main.py lines 10-19 - Current imports to review

  **Acceptance Criteria**:
  - [ ] No unused import warnings when running Python

- [ ] 2. Extract duplicated success output to shared function

  **What to do**:
  - Create `_print_generation_success()` function to handle the duplicated output
  - Update both `run_with_tui` and `run_cli` to use the shared function

  **Must NOT do**:
  - Change the output format (must remain identical)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple refactor, single file
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: Task 1

  **References**:
  - main.py lines 488-512 - Duplicated code in run_with_tui
  - main.py lines 573-597 - Duplicated code in run_cli

  **Acceptance Criteria**:
  - [ ] Function extracted successfully
  - [ ] Both code paths use the function
  - [ ] Output format unchanged

- [ ] 3. Fix misleading TUI progress steps

  **What to do**:
  - Remove or fix fake "completed" steps that don't reflect actual work
  - The guide scraping happens inside `run_timeline_generation()` - either:
    - Remove guide steps from TUI display (they're internal to the agent)
    - Or show them as part of a single "generating" step
  - Rename "Researching ability targets" to accurately reflect what happens

  **Must NOT do**:
  - Change the actual workflow (only fix display)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple fix to TUI display logic
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: Task 2

  **References**:
  - main.py lines 51-62 - TUI steps definition
  - main.py lines 438-439 - Fake guide completed steps
  - main.py lines 455-459 - Fake targets step

  **Acceptance Criteria**:
  - [ ] No misleading "completed" steps without actual work
  - [ ] Step names accurately reflect what's happening

- [ ] 4. Test interactive and TUI modes

  **What to do**:
  - Run the CLI to verify both modes work

  **Must NOT do**:
  - Break existing functionality

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Verification testing
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: Task 3

  **References**:
  - run.py - Entry point

  **Acceptance Criteria**:
  - [ ] `python3 run.py --help` works
  - [ ] `python3 run.py list-bosses` works
  - [ ] Interactive mode command works

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit**
  Verify all tasks completed as specified
  
- [ ] F2. **Code Quality Review**
  Run python syntax check, verify no errors

- [ ] F3. **Functional Test**
  Run CLI commands to verify they work

---

## Commit Strategy

- **Single commit**: `refactor(tui): clean up TUI integration`

---

## Success Criteria

### Verification Commands
```bash
python3 run.py --help  # Should work without errors
python3 run.py list-bosses  # Should list bosses
```

### Final Checklist
- [ ] All unused imports removed
- [ ] Duplicated code extracted
- [ ] No misleading progress steps
- [ ] Both modes work correctly
