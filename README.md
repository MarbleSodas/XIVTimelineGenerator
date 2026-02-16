# FFXIV Timeline Scraper

AI-powered timeline scraper for FFXIV raid boss timelines using atomic agents. Instead of hard-coded rules, this scraper uses specialized agents that interpret data dynamically to extract meaningful insights.

## Philosophy: Agents Over Rules

Most timeline scrapers rely on hard-coded patterns:
- "If damage > 50000, it's a tank buster"
- "If name contains 'raidwide', it's an AoE"
- "This boss always uses Ability X at 60 seconds"

**This scraper is different.** It uses **atomic agents** that analyze the actual data and learn patterns:

- **No hard-coded thresholds** - Agents calculate dynamic thresholds based on actual damage distributions
- **No hard-coded tank buster rules** - Agents detect tank busters by analyzing target counts and damage patterns
- **No hard-coded ability mappings** - Agents correlate abilities across reports using fuzzy matching
- **No hard-coded timelines** - Agents detect variations and determine defaults statistically

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              TimelineGenerationOrchestrator                       │
│                  (Agent Pipeline)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │ CactbotTimeline │    │  FFLogsReport   │                  │
│  │     Agent       │    │      Agent       │                  │
│  └────────┬────────┘    └────────┬─────────┘                  │
│           │                      │                               │
│           │      ┌───────────────┴───────────────┐              │
│           │      │                               │              │
│           ▼      ▼                               ▼              │
│  ┌──────────────────┐    ┌──────────────────┐                │
│  │DamageEventExtractor│    │TimelineVariantDetector│            │
│  │     Agent       │    │      Agent       │                │
│  └────────┬────────┘    └────────┬─────────┘                  │
│           │                      │                               │
│           └───────────┬───────────┘                              │
│                       ▼                                          │
│  ┌──────────────────────────────┐                               │
│  │   TimelineAggregatorAgent    │                               │
│  │   (Statistical Interpretation)│                              │
│  └──────────────┬───────────────┘                               │
│                 ▼                                                │
│  ┌──────────────────────────────┐                               │
│  │   TimelineBuilderAgent        │                               │
│  └──────────────────────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## How Agents Interpret Data

### 1. CactbotTimelineAgent - Adaptive Parsing

Instead of hard-coded regex patterns, the agent:
- Parses timeline syntax dynamically
- Extracts metadata (hit counts, durations) when present
- Filters dodgeable abilities based on pattern recognition
- Handles variations in Cactbot timeline formats

### 2. FFLogsReportAgent - Contextual Discovery

Instead of fixed API calls, the agent:
- Discovers relevant reports based on kill quality
- Validates fight data meets minimum standards
- Extracts master data (abilities, actors) per report
- Handles API rate limits and errors gracefully

### 3. DamageEventExtractorAgent - Intelligent Correlation

Instead of exact timestamp matching, the agent:
- Uses fuzzy matching to correlate abilities across different naming conventions
- Syncs FFLogs timestamps to Cactbot timeline with configurable windows
- Filters auto-attacks and low-damage events
- Determines damage types (physical/magical) from hit type data

### 4. TimelineVariantDetectorAgent - Pattern Recognition

Instead of hard-coded timeline branches, the agent:
- Buckets actions by time proximity (not fixed intervals)
- Clusters similar actions across multiple reports
- Identifies branching points where timelines diverge
- Calculates occurrence frequencies to determine default path

### 5. TimelineAggregatorAgent - Statistical Analysis

Instead of fixed damage thresholds, the agent:
- Calculates **dynamic thresholds** from actual data distribution (p50/p75/p90)
- Uses **IQR filtering** to remove outliers automatically
- Computes **median damage** (not mean) for robustness
- Detects tank busters from **target count patterns** + damage levels

### 6. TimelineBuilderAgent - Contextual Output

Instead of template-based output, the agent:
- Generates descriptions based on ability name analysis
- Assigns importance levels dynamically from damage rankings
- Includes variant information for decision-making
- Formats output for MitPlan consumption

## Installation

```bash
git clone https://github.com/MitPlan/timeline-scraper.git
cd timeline-scraper
pip install -e .
```

## Configuration

```env
MITPLAN_FFLOGS_CLIENT_ID=your_client_id
MITPLAN_FFLOGS_CLIENT_SECRET=your_client_secret
```

Get FFLogs API credentials at https://www.fflogs.com/profile

## Usage

```bash
# List available bosses
python -m cli.main list-bosses

# Generate timeline
python -m cli.main generate m7s --count 50

# Show boss info
python -m cli.main info m7s
```

## Output

```json
{
  "name": "Brute Abominator",
  "boss_id": "m7s",
  "actions": [
    {
      "id": "frontal_acleave_1",
      "name": "Frontal Acleave",
      "time": 12.4,
      "unmitigatedDamage": "~45000",
      "damageType": "physical",
      "importance": "high",
      "isTankBuster": true,
      "targetCountMedian": 1.0
    }
  ],
  "default_actions": [...],
  "all_variants": {
    "120s": ["Ability A", "Ability B"]
  }
}
```

## Damage Processing: No Hard-Coded Rules

Traditional scrapers use fixed thresholds like `if damage > 50000: tank_buster = true`

**Our approach:**
```python
# Calculate thresholds from actual data distribution
thresholds = calculate_damage_thresholds(occurrences)
# Returns: {"p50": 15000, "p75": 35000, "p90": 65000}

# Determine importance dynamically
if damage >= thresholds["p90"]:
    importance = "critical"
elif damage >= thresholds["p75"]:
    importance = "high"
# ... etc
```

## Variant Detection: No Hard-Coded Paths

Traditional scrapers define expected ability sequences

**Our approach:**
```python
# Bucket actions by time proximity
buckets = bucket_actions_by_proximity(events, window=15.0)

# Find where timelines diverge
variants = identify_branches(buckets, min_ratio=0.3)

# Determine default from frequency
default = most_common(sequences)
```

## Development

```bash
pip install -e ".[dev]"
pytest
mypy agents tools schemas
```

## License

MIT
