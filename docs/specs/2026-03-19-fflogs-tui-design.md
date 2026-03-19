# FFLogs Report Fetcher — TUI + API Integration Spec

**Date:** 2026-03-19
**Status:** Draft

---

## 1. Overview

A Python TUI application that fetches 30 most recent clears for a selected FFXIV raid/ultimate boss from FFLogs. Built with Textual for the TUI and `fflogsapi` for API interaction.

**Scope (this phase):**
- Encounter selection via TUI
- FFLogs API authentication and data fetching
- Sequential fetch of 30 reports per selected boss
- Clean result display

**Out of scope (future phases):**
- Post-fetch processing of reports
- Atomic agents integration (stub slot only)

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         TUI Layer                            │
│  Textual App: RaidSelector → BossSelector → Fetch → Results │
└────────────────────────────┬─────────────────────────────────┘
                             │ imports
┌────────────────────────────▼─────────────────────────────────┐
│                   fflogs Package (src/fflogs/)               │
│                                                              │
│  • auth.py       — OAuth2 client-credentials token mgmt     │
│  • cache.py      — Disk cache (token + encounter IDs)      │
│  • client.py     — FFLogsClient wrapping fflogsapi          │
│  • encounters.py — Encounter dataclass + YAML loader        │
│  • models.py     — Report, Fight dataclasses                │
└────────────────────────────┬─────────────────────────────────┘
                             │ future extension
┌────────────────────────────▼─────────────────────────────────┐
│                   agents Package (src/agents/)               │
│  Stub slot for future atomic agents (does nothing this phase)│
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

- **TUI never calls the FFLogs API directly** — goes through `fflogs/` package only
- **`fflogsapi` package** (halworsen/fflogsapi on PyPI) wraps the v2 GraphQL API
- **YAML encounter config** — no hardcoded IDs in Python; resolved at runtime and cached
- **Agents are a future extension point** — interface is stubbed, not implemented

---

## 3. Encounter Mapping

### Data Model

```python
@dataclass(frozen=True)
class Encounter:
    code: str          # "M11S"
    full_name: str     # "AAC Heavyweight M3 (Savage)"
    boss_name: str     # "The Tyrant"
    zone_id: int       # FFLogs numeric zone ID
    encounter_id: int | None  # resolved from API if null
    expansion: str     # "dawntrail"
    category: str      # "savage" | "ultimate"
```

### Config Files (YAML)

```
data/encounters/
├── dawntrail.yaml      # M1S–M4S, M5S–M8S, M9S–M12S, FRU
├── endwalker.yaml      # P1S–P12S, TOP, DSR
├── shadowbringers.yaml  # E1S–E12S, UCoB, UWU, TEA
└── stormblood.yaml     # O1S–O12S
```

`encounter_id` is `null` in YAML — resolved from FFLogs API on first run and cached to `~/.xivtimelinegenerator/cache/encounters.json`.

### Boss Mappings

#### Dawntrail Savage (The Arcadion)

**AAC Light-heavyweight Tier (Patch 7.0)**
| Code | Full Name | Boss | Zone ID |
|------|-----------|------|---------|
| M1S | AAC Light-heavyweight M1 (Savage) | Black Cat | 62 |
| M2S | AAC Light-heavyweight M2 (Savage) | Honey B. Lovely | 62 |
| M3S | AAC Light-heavyweight M3 (Savage) | Brute Bomber | 62 |
| M4S | AAC Light-heavyweight M4 (Savage) | Wicked Thunder | 62 |

**AAC Cruiserweight Tier (Patch 7.2)**
| Code | Full Name | Boss | Zone ID |
|------|-----------|------|---------|
| M5S | AAC Cruiserweight M1 (Savage) | Dancing Green | 68 |
| M6S | AAC Cruiserweight M2 (Savage) | Sugar Riot | 68 |
| M7S | AAC Cruiserweight M3 (Savage) | Brute Abombinator | 68 |
| M8S | AAC Cruiserweight M4 (Savage) | Howling Blade | 68 |

**AAC Heavyweight Tier (Patch 7.4)**
| Code | Full Name | Boss | Zone ID |
|------|-----------|------|---------|
| M9S | AAC Heavyweight M1 (Savage) | Vamp Fatale | 73 |
| M10S | AAC Heavyweight M2 (Savage) | Red Hot and Deep Blue | 73 |
| M11S | AAC Heavyweight M3 (Savage) | The Tyrant | 73 |
| M12S | AAC Heavyweight M4 (Savage) | Lindwurm / Lindwurm II | 73 |

#### Ultimates

| Code | Full Name | Zone ID |
|------|-----------|---------|
| FRU | Futures Rewritten (Ultimate) | 65 |
| TOP | The Omega Protocol (Ultimate) | 59 |
| DSR | Dragonsong's Reprise (Ultimate) | 41 |

#### Endwalker Savage (Pandaemonium)

| Code | Full Name | Zone ID |
|------|-----------|---------|
| P1S | Asphodelos: The First Circle (Savage) | — |
| P2S | Asphodelos: The Second Circle (Savage) | — |
| P3S | Asphodelos: The Third Circle (Savage) | — |
| P4S | Asphodelos: The Fourth Circle (Savage) | — |
| P5S | Abyssos: The Fifth Circle (Savage) | — |
| P6S | Abyssos: The Sixth Circle (Savage) | — |
| P7S | Abyssos: The Seventh Circle (Savage) | — |
| P8S | Abyssos: The Eighth Circle (Savage) | — |
| P9S | Anabaseios: The Ninth Circle (Savage) | — |
| P10S | Anabaseios: The Tenth Circle (Savage) | — |
| P11S | Anabaseios: The Eleventh Circle (Savage) | — |
| P12S | Anabaseios: The Twelfth Circle (Savage) | — |

(Full zone IDs for Endwalker tiers to be filled in from FFLogs API at runtime)

#### Legacy Ultimates

| Code | Full Name |
|------|-----------|
| UCoB | The Unending Coil of Bahamut (Ultimate) |
| UWU | The Weapon's Refrain (Ultimate) |
| TEA | The Epic of Alexander (Ultimate) |

---

## 4. FFLogs API Integration

### Credentials

```
FFLOGS_CLIENT_ID=a14508fc-5d09-418f-a1db-01879a8eaf14
FFLOGS_CLIENT_SECRET=Q9YZmTib56VT6AGNhuQQ2iPDJiFLVYFiMLYmsQN9
```

### OAuth Flow

- **Grant type:** client credentials (machine-to-machine)
- **Token URL:** `https://www.fflogs.com/oauth/token`
- **API URL:** `https://www.fflogs.com/api/v2/client/`
- Token cached to `~/.xivtimelinegenerator/cache/token.json` with expiry
- Refresh automatically when expired

### Cache Location

```
~/.xivtimelinegenerator/cache/
├── token.json         # OAuth token
└── encounters.json    # resolved encounter IDs
```

### Fetching Reports

For a selected boss:
1. Resolve `encounter_id` from cache or API (`client.get_zone(zone_id).encounters`)
2. Query `client.get_reports(zone=zone_id, boss=encounter_id, difficulty=101, limit=30)`
3. Filter to kills only (`kill_type=kills`)

### Rate Limiting

- Respect `X-RateLimit-*` headers from API responses
- On 429: read `Retry-After` header, back off accordingly
- `fflogsapi` package handles some of this automatically

---

## 5. TUI Specification

### Screen Flow

```
RaidSelectorScreen
    │
    ├── Expansion selected → Tier/Ultimate selected → BossSelectorScreen
    │                                                           │
    │                        └── Boss selected → FetchScreen ──→ ResultsScreen
    │
    └── Ultimate selected (single boss) → BossSelectorScreen (pre-selected)
```

### Screen 1: RaidSelectorScreen

- `Tree` widget showing: Expansion → Tier/Ultimate → Individual Boss
- Selecting an **expansion** expands to show tiers/ultimates
- Selecting a **tier** expands to show individual bosses
- Selecting an **ultimate** goes directly to BossSelectorScreen (single boss pre-selected)
- `[Select →]` button disabled until a boss is selected

**Tree structure:**
```
▼ Dawntrail
  ├── AAC Light-heavyweight (M1S–M4S)
  │     ● M1S — Black Cat
  │     ● M2S — Honey B. Lovely
  │     ● M3S — Brute Bomber
  │     ● M4S — Wicked Thunder
  ├── AAC Cruiserweight (M5S–M8S)
  ├── AAC Heavyweight (M9S–M12S)
  └── Futures Rewritten (FRU)
▼ Endwalker
  ├── Anabaseios (P9S–P12S)
  ├── Abyssos (P5S–P8S)
  ├── Asphodelos (P1S–P4S)
  ├── The Omega Protocol (TOP)
  └── Dragonsong's Reprise (DSR)
▼ Shadowbringers
  └── ...
▼ Stormblood
  └── ...
```

### Screen 2: BossSelectorScreen

- Header: "Select Bosses for {Tier Name}"
- `Checkbox` list of all bosses in the tier
- Multi-select enabled
- "Select All" / "Clear All" shortcuts
- `[← Back]` and `[Fetch Reports →]` buttons

### Screen 3: FetchScreen

- Shown while fetching
- Per-boss progress: "Fetching M11S... (3/30)"
- Sequential fetch: one boss at a time
- Cancel button
- On error: show error message with retry option

### Screen 4: ResultsScreen

- `DataTable` with columns: Report ID | Date | Duration | Kill % | Guild
- Sorted by date descending
- `[← Back]` to re-select
- `[Export]` button (future)
- Row count shown: "30 reports for M11S"

### Styling

- Dark theme (Textual default dark)
- Accent color: blue
- Monospace font for report IDs and codes
- Compact layout suitable for 80-column terminals

---

## 6. Project Structure

```
XIVTimelineGenerator/
├── src/
│   ├── __init__.py
│   ├── fflogs/
│   │   ├── __init__.py
│   │   ├── auth.py          # OAuth token management
│   │   ├── cache.py         # Disk cache (token + encounter IDs)
│   │   ├── client.py        # FFLogsClient wrapper
│   │   ├── encounters.py    # Encounter dataclass + YAML loader
│   │   └── models.py        # Report, Fight dataclasses
│   ├── agents/              # future atomic agents slot
│   │   └── __init__.py      # stub: "plug in agents here in the future"
│   └── tui/
│       ├── __init__.py
│       ├── app.py           # Textual App
│       ├── screens/
│       │   ├── __init__.py
│       │   ├── raid_selector.py
│       │   ├── boss_selector.py
│       │   ├── fetching.py
│       │   └── results.py
│       └── widgets/
│           └── __init__.py
├── data/
│   └── encounters/
│       ├── dawntrail.yaml
│       ├── endwalker.yaml
│       ├── shadowbringers.yaml
│       └── stormblood.yaml
├── tests/
│   ├── __init__.py
│   ├── test_fflogs_client.py
│   └── test_encounters.py
├── docs/
│   └── specs/
│       └── 2026-03-19-fflogs-tui-design.md
├── pyproject.toml
└── README.md
```

---

## 7. Dependencies

```
textual>=0.50.0
fflogsapi>=2.1.0
pyyaml>=6.0
```

---

## 8. Environment Variables

```
FFLOGS_CLIENT_ID=a14508fc-5d09-418f-a1db-01879a8eaf14
FFLOGS_CLIENT_SECRET=Q9YZmTib56VT6AGNhuQQ2iPDJiFLVYFiMLYmsQN9
```

---

## 9. Future: Atomic Agents Integration Point

`src/agents/__init__.py` is a stub. When atomic agents are added in a future phase, the interface will be:

```python
# agents/__init__.py (future)
def process_reports(reports: list[Report], boss: Encounter) -> Any:
    """Atomic agent processing slot — implement in future phases."""
    raise NotImplementedError("atomic agents not yet integrated")
```

The `ResultsScreen` will gain an "Process →" button that calls into this slot.

---

## 10. Acceptance Criteria

- [ ] TUI launches and displays RaidSelectorScreen
- [ ] Expansion → tier → boss tree navigation works
- [ ] BossSelectorScreen shows correct bosses for selected tier
- [ ] OAuth token is fetched and cached on first run
- [ ] Encounter IDs are resolved from API and cached on first run
- [ ] Fetching 30 reports for a boss works and shows progress
- [ ] Results are displayed in a table
- [ ] Sequential fetch for multiple bosses works (one after another)
- [ ] Rate limit 429 is handled gracefully (backoff + retry)
- [ ] Error states are shown (network failure, auth failure, API errors)
- [ ] All YAML encounter configs load correctly
- [ ] Tests pass for fflogs client and encounter loading
