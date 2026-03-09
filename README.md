# XIV Timeline Generator

AI-powered FFXIV boss timeline generator using Pydantic AI with MiniMax M2.5 support.

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
python3 run.py generate p12s --tui

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

## TUI Mode

The TUI mode provides real-time observability into the timeline generation process during direct boss generation:

```
┌─ XIV Timeline Generator - p12s ──────────────────────────────┐
│                                                            │
│  ● Fetching cactbot data...                               │
│  ○ Scraping Icy Veins guide                               │
│  ○ Scraping Hardcore Gamer guide                           │
│  ○ Processing timeline entries                             │
│  ○ Extracting phases and variations                        │
│  ○ Generating output files                                 │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

Use `--tui` or `-u` flag with `generate` command:
```bash
python3 run.py generate p12s --tui
python3 run.py generate zodiark -u
```

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
- `--tui`: Enable TUI mode for observability
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
- Minimax API key (or OpenAI-compatible API)

## Environment Variables

```bash
MINIMAX_API_KEY=your-api-key-here
MINIMAX_BASE_URL=https://api.minimax.chat/v1
MINIMAX_MODEL=MiniMax-M2.5
```

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
Agent (Pydantic AI + MiniMax M2.5)
    │
    ├─► CactbotClient ──────► GitHub (timeline data)
    │
    ├─► GuideScraper ───────► Icy Veins / Hardcore Gamer
    │
    └─► TimelineSynthesizer ─► Merged output (JSON + Cactbot)
```
