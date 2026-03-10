# XIV Timeline Generator

AI-powered FFXIV boss timeline generator using LangGraph with MiniMax M2.5 support.

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your Minimax API key

# Run interactive TUI (default - shows boss selection menu)
python3 run.py

# Run interactive mode explicitly
python3 run.py interactive

# Generate timeline for specific boss directly
python3 run.py generate p12s

# List all available bosses
python3 run.py list-bosses
```

## Interactive Mode

The interactive mode provides a navigable boss selection menu:

```
 XIV Timeline Generator - Select a Boss 
 ─────────────────────────────────────────
   Dawntrail
     [Trials]
       doomtrain (Savage)
       zoraal_ja (Savage)
     [Raids]
       m1s - Savage
       m2s - Savage
       ...
   Endwalker
     [Ultimates]
       dsr, top
     [Trials]
       barbariccia, endsinger, zodiark
     [Raids]
       p1s - p12s

 [↑↓] Scroll  [Enter] Select  [Q] Quit
```

Use arrow keys to navigate, Enter to select, Q to quit. After generating a timeline, you can choose to generate another or quit.

## Features

- **Interactive Boss Selection**: Navigable menu organized by expansion and encounter type
- **TUI Progress Display**: Visual progress tracking showing each step of timeline generation
- **Data Sources**: Fetches timeline data from cactbot GitHub repository
- **Strategy Guides**: Scrapes boss guides from Icy Veins and Hardcore Gamer
- **Synthesis**: Combines multiple sources into accurate timelines with phase variations
- **Output Formats**: JSON and Cactbot-compatible timeline text
- **Caching**: Local 7-day cache for cactbot data

## CLI Options

```bash
# Generate timeline for a boss
python3 run.py generate p12s
python3 run.py generate zodiark --expansion 06-ew
python3 run.py generate m12s --output ./timelines

# List available bosses
python3 run.py list-bosses

# Clear cache
python3 run.py cache-clear

# Help
python3 run.py --help
```

### Options

- `--expansion, -e`: Expansion code (06-ew, 05-shb, etc.)
- `--type, -t`: Encounter type (raid, trial, ultimate)
- `--difficulty, -d`: Difficulty (n, s, u)
- `--output, -o`: Output directory (default: ./output)
- `--verbose, -v`: Verbose output

Note: All CLI examples use `python3 run.py` as the entry point. Alternatively, you can install the package with `pip install -e .` and use `xiv-timeline` directly.

## Supported Bosses

The tool supports all FFXIV raids, trials, and ultimates from A Realm Reborn to Dawntrail:

- **Dawntrail (07-dt)**: M1S-M12S, Trials
- **Endwalker (06-ew)**: P1S-P12S, Zodiark, Endsinger, TOP, DSR
- **Shadowbringers (05-shb)**: E1S-E12S, TEA, UCOB
- **Stormblood (04-sb)**: O1S-O12S, Ultima (UWu)
- **Heavensward (03-hw)**: A1S-A12S

## Requirements

- Python 3.11+
- Minimax API key (or any OpenAI-compatible API)

## Environment Variables

```bash
MINIMAX_API_KEY=your-api-key-here
MINIMAX_BASE_URL=https://api.minimax.chat/v1
MINIMAX_MODEL=MiniMax-M2.5
```

## Observability & Debugging

### Verbose Logging

Pass `--verbose` / `-v` to see per-node timing, data sizes, and LLM call details:

```bash
python3 run.py generate p12s -v
```

Example output:
```
[fetch_cactbot] Starting — boss=p12s, expansion=06-ew
[fetch_cactbot] Done in 0.42s — 87 entries, 3 phases
[fetch_guides]  Done in 1.13s — succeeded: ['icy-veins'], failed: ['hardcore-gamer']
[synthesize]    LLM call succeeded in 2.31s — 3 phases returned
[research_targets] Done in 0.01s — 45 abilities analyzed, 2 multi-hit
[export]        Done in 0.00s — 2847 chars of export text
```

### LangSmith Tracing

For full production-grade observability (traces, LLM call inspection, cost tracking), enable [LangSmith](https://smith.langchain.com):

```bash
# Add to your .env file:
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=xiv-timeline-generator   # optional, defaults to this
```

When enabled, every graph node execution, LLM call (including inputs/outputs/tokens), and state transition is automatically traced and viewable in the LangSmith dashboard.

## Output

Generated timelines include:

- **JSON**: Complete structured data with phases, variations, notes
- **Cactbot Timeline**: Ready to use with the OverlayPlugin cactbot timeline
- **Synthesized Timeline**: Timeline with guide annotations and tips

## Architecture

```
CLI/TUI
    │
    ▼
LangGraph StateGraph (5-node pipeline)
    │
    ├─► fetch_cactbot ─────► GitHub (timeline data)
    │
    ├─► fetch_guides ──────► Icy Veins / Hardcore Gamer
    │
    ├─► synthesize ────────► LLM (MiniMax M2.5) + local synthesis
    │
    ├─► research_targets ──► Ability target inference
    │
    └─► export ────────────► Cactbot-compatible timeline text
```

The core generation pipeline is a LangGraph `StateGraph` that:
1. Fetches raw cactbot timeline data from GitHub.
2. Scrapes strategy guides from Icy Veins and Hardcore Gamer.
3. Uses the LLM to synthesize a structured timeline (with local fallback).
4. Researches ability targets and multi-hit info.
5. Outputs the final structured JSON and Cactbot export texts.

## Development & Testing

If you want to contribute or run the automated tests, install the package with development dependencies and run `pytest`:

```bash
# Install development dependencies
pip3 install -e ".[dev]"

# Run tests
python3 -m pytest tests/ -v
```
