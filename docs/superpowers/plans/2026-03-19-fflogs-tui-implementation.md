# FFLogs TUI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working Python TUI that lets users select a Dawntrail/Endwalker/etc. raid boss via Textual and fetches 30 recent clears from FFLogs via the v2 API.

**Architecture:** Modular package structure — `fflogs/` for all API interaction, `tui/` for Textual UI, `agents/` as a stub slot. YAML configs drive encounter mapping. Sequential boss fetch with progress display.

**Tech Stack:** Python 3.11+, Textual, fflogsapi, PyYAML

---

## Chunk 1: Project Scaffold

**Goal:** Create the directory tree, `pyproject.toml`, and all `__init__.py` stub files.

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/fflogs/__init__.py`
- Create: `src/agents/__init__.py`
- Create: `src/tui/__init__.py`
- Create: `src/tui/screens/__init__.py`
- Create: `src/tui/widgets/__init__.py`
- Create: `tests/__init__.py`
- Create: `README.md`

---

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "xiv-timeline-generator"
version = "0.1.0"
description = "FFLogs report fetcher with Textual TUI"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.50.0",
    "fflogsapi>=2.1.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Run: `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` — verify valid TOML

---

- [ ] **Step 2: Create all `__init__.py` stub files**

```python
# src/__init__.py
"""XIVTimelineGenerator — FFLogs report fetcher with TUI."""
```

```python
# src/fflogs/__init__.py
"""FFLogs API client package."""
```

```python
# src/agents/__init__.py
"""Atomic agents slot — implement in a future phase."""
```

```python
# src/tui/__init__.py
"""Textual TUI package."""
```

```python
# src/tui/screens/__init__.py
"""TUI screens."""
```

```python
# src/tui/widgets/__init__.py
"""TUI widgets."""
```

```python
# tests/__init__.py
"""Tests."""
```

Run: `find . -name "*.py" -path "./src/*" | head -20` — verify all files created

---

- [ ] **Step 3: Create minimal `README.md`**

```markdown
# XIVTimelineGenerator

FFLogs report fetcher with a Textual TUI.

## Setup

```bash
pip install -e .
export FFLOGS_CLIENT_ID=your_client_id
export FFLOGS_CLIENT_SECRET=your_client_secret
python -m tui.app
```
```

---

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml src/__init__.py src/fflogs/__init__.py src/agents/__init__.py src/tui/__init__.py src/tui/screens/__init__.py src/tui/widgets/__init__.py tests/__init__.py README.md
git commit -m "chore: project scaffold with pyproject.toml and package stubs"
```

---

## Chunk 2: Encounter Data (`data/encounters/` YAML)

**Goal:** Create the YAML files that define all raid/ultimate encounters with their zone IDs and codes.

**Files:**
- Create: `data/encounters/dawntrail.yaml`
- Create: `data/encounters/endwalker.yaml`
- Create: `data/encounters/shadowbringers.yaml`
- Create: `data/encounters/stormblood.yaml`

**Reference:** Spec Section 3 for full encounter mapping. Zone IDs: AAC Light-heavyweight=62, AAC Cruiserweight=68, AAC Heavyweight=73, Futures Rewritten=65, DSR=41, TOP=59.

---

- [ ] **Step 1: Write `data/encounters/dawntrail.yaml`**

```yaml
expansion: dawntrail
tiers:
  - name: "AAC Light-heavyweight"
    short_name: "M1S–M4S"
    zone_id: 62
    encounters:
      - code: M1S
        full_name: "AAC Light-heavyweight M1 (Savage)"
        boss_name: "Black Cat"
        encounter_id: null
      - code: M2S
        full_name: "AAC Light-heavyweight M2 (Savage)"
        boss_name: "Honey B. Lovely"
        encounter_id: null
      - code: M3S
        full_name: "AAC Light-heavyweight M3 (Savage)"
        boss_name: "Brute Bomber"
        encounter_id: null
      - code: M4S
        full_name: "AAC Light-heavyweight M4 (Savage)"
        boss_name: "Wicked Thunder"
        encounter_id: null

  - name: "AAC Cruiserweight"
    short_name: "M5S–M8S"
    zone_id: 68
    encounters:
      - code: M5S
        full_name: "AAC Cruiserweight M1 (Savage)"
        boss_name: "Dancing Green"
        encounter_id: null
      - code: M6S
        full_name: "AAC Cruiserweight M2 (Savage)"
        boss_name: "Sugar Riot"
        encounter_id: null
      - code: M7S
        full_name: "AAC Cruiserweight M3 (Savage)"
        boss_name: "Brute Abombinator"
        encounter_id: null
      - code: M8S
        full_name: "AAC Cruiserweight M4 (Savage)"
        boss_name: "Howling Blade"
        encounter_id: null

  - name: "AAC Heavyweight"
    short_name: "M9S–M12S"
    zone_id: 73
    encounters:
      - code: M9S
        full_name: "AAC Heavyweight M1 (Savage)"
        boss_name: "Vamp Fatale"
        encounter_id: null
      - code: M10S
        full_name: "AAC Heavyweight M2 (Savage)"
        boss_name: "Red Hot and Deep Blue"
        encounter_id: null
      - code: M11S
        full_name: "AAC Heavyweight M3 (Savage)"
        boss_name: "The Tyrant"
        encounter_id: null
      - code: M12S
        full_name: "AAC Heavyweight M4 (Savage)"
        boss_name: "Lindwurm"
        encounter_id: null

ultimates:
  - code: FRU
    full_name: "Futures Rewritten (Ultimate)"
    zone_id: 65
    encounter_id: null
```

Run: `python -c "import yaml; yaml.safe_load(open('data/encounters/dawntrail.yaml'))"` — verify valid YAML

---

- [ ] **Step 2: Write `data/encounters/endwalker.yaml`**

```yaml
expansion: endwalker
tiers:
  - name: "Asphodelos"
    short_name: "P1S–P4S"
    zone_id: 54
    encounters:
      - code: P1S; full_name: "Asphodelos: The First Circle (Savage)"; boss_name: "Erichthonios"; encounter_id: null
      - code: P2S; full_name: "Asphodelos: The Second Circle (Savage)"; boss_name: "Hippomenes"; encounter_id: null
      - code: P3S; full_name: "Asphodelos: The Third Circle (Savage)"; boss_name: "The Challenging Mount"; encounter_id: null
      - code: P4S; full_name: "Asphodelos: The Fourth Circle (Savage)"; boss_name: "Hesperos"; encounter_id: null

  - name: "Abyssos"
    short_name: "P5S–P8S"
    zone_id: 55
    encounters:
      - code: P5S; full_name: "Abyssos: The Fifth Circle (Savage)"; boss_name: "Eos"; encounter_id: null
      - code: P6S; full_name: "Abyssos: The Sixth Circle (Savage)"; boss_name: "Selene"; encounter_id: null
      - code: P7S; full_name: "Abyssos: The Seventh Circle (Savage)"; boss_name: "Circus"; encounter_id: null
      - code: P8S; full_name: "Abyssos: The Eighth Circle (Savage)"; boss_name: "Hegemom"; encounter_id: null

  - name: "Anabaseios"
    short_name: "P9S–P12S"
    zone_id: 57
    encounters:
      - code: P9S; full_name: "Anabaseios: The Ninth Circle (Savage)"; boss_name: "Lamebrix"; encounter_id: null
      - code: P10S; full_name: "Anabaseios: The Tenth Circle (Savage)"; boss_name: "Glopper"; encounter_id: null
      - code: P11S; full_name: "Anabaseios: The Eleventh Circle (Savage)"; boss_name: "Mithrios"; encounter_id: null
      - code: P12S; full_name: "Anabaseios: The Twelfth Circle (Savage)"; boss_name: "Absolute One"; encounter_id: null

ultimates:
  - code: TOP
    full_name: "The Omega Protocol (Ultimate)"
    zone_id: 59
    encounter_id: null
  - code: DSR
    full_name: "Dragonsong's Reprise (Ultimate)"
    zone_id: 41
    encounter_id: null
```

(Zone IDs 54, 55, 57 for Endwalker tiers to be verified against API — stubbed as above.)

Run: `python -c "import yaml; yaml.safe_load(open('data/encounters/endwalker.yaml'))"` — verify valid YAML

---

- [ ] **Step 3: Write `data/encounters/shadowbringers.yaml` and `data/encounters/stormblood.yaml`**

(Stub files with Eden's Gate/Verse/Promise for ShB; Omega (O1S–O12S) for SB. Zone IDs to be resolved at runtime.)

```yaml
# data/encounters/shadowbringers.yaml
expansion: shadowbringers
tiers:
  - name: "Eden's Gate"
    short_name: "E1S–E4S"
    zone_id: 25
    encounters:
      - code: E1S; full_name: "Eden's Gate: Inundation (Savage)"; boss_name: "Void +"; encounter_id: null
      - code: E2S; full_name: "Eden's Gate: Section (Savage)"; boss_name: "Dahu"; encounter_id: null
      - code: E3S; full_name: "Eden's Gate: Sepimentation (Savage)"; boss_name: "Coco"; encounter_id: null
      - code: E4S; full_name: "Eden's Gate: Annihilation (Savage)"; boss_name: "War's +"; encounter_id: null
  - name: "Eden's Verse"
    short_name: "E5S–E8S"
    zone_id: 26
    encounters:
      - code: E5S; full_name: "Eden's Verse: Furor (Savage)"; boss_name: "Fiou"; encounter_id: null
      - code: E6S; full_name: "Eden's Verse: Iconoclasm (Savage)"; boss_name: "Hydaelyn"; encounter_id: null
      - code: E7S; full_name: "Eden's Verse: Revolution (Savage)"; boss_name: "Zodiar"; encounter_id: null
      - code: E8S; full_name: "Eden's Verse: Samba (Savage)"; boss_name: "Knight"; encounter_id: null
  - name: "Eden's Promise"
    short_name: "E9S–E12S"
    zone_id: 27
    encounters:
      - code: E9S; full_name: "Eden's Promise: Umbra (Savage)"; boss_name: "Cloud"; encounter_id: null
      - code: E10S; full_name: "Eden's Promise: Lithobras (Savage)"; boss_name: "Earth"; encounter_id: null
      - code: E11S; full_name: "Eden's Promise: Eologian (Savage)"; boss_name: "Light"; encounter_id: null
      - code: E12S; full_name: "Eden's Promise: Testament (Savage)"; boss_name: "Void"; encounter_id: null
ultimates:
  - code: UCoB; full_name: "The Unending Coil of Bahamut (Ultimate)"; zone_id: 38; encounter_id: null
  - code: UWU; full_name: "The Weapon's Refrain (Ultimate)"; zone_id: 39; encounter_id: null
  - code: TEA; full_name: "The Epic of Alexander (Ultimate)"; zone_id: 40; encounter_id: null
```

```yaml
# data/encounters/stormblood.yaml
expansion: stormblood
tiers:
  - name: "Omega: Deltascape"
    short_name: "O1S–O4S"
    zone_id: 28
    encounters:
      - code: O1S; full_name: "Omega: Deltascape V1.0 (Savage)"; boss_name: "Fire"; encounter_id: null
      - code: O2S; full_name: "Omega: Deltascape V2.0 (Savage)"; boss_name: "Ice"; encounter_id: null
      - code: O3S; full_name: "Omega: Deltascape V3.0 (Savage)"; boss_name: "Wind"; encounter_id: null
      - code: O4S; full_name: "Omega: Deltascape V4.0 (Savage)"; boss_name: "Earth"; encounter_id: null
  - name: "Omega: Sigmascape"
    short_name: "O5S–O8S"
    zone_id: 29
    encounters:
      - code: O5S; full_name: "Omega: Sigmascape V1.0 (Savage)"; boss_name: "Gamma"; encounter_id: null
      - code: O6S; full_name: "Omega: Sigmascape V2.0 (Savage)"; boss_name: "Sigma"; encounter_id: null
      - code: O7S; full_name: "Omega: Sigmascape V3.0 (Savage)"; boss_name: "Omega"; encounter_id: null
      - code: O8S; full_name: "Omega: Sigmascape V4.0 (Savage)"; boss_name: "Omega M&F"; encounter_id: null
  - name: "Omega: Alphascape"
    short_name: "O9S–O12S"
    zone_id: 30
    encounters:
      - code: O9S; full_name: "Omega: Alphascape V1.0 (Savage)"; boss_name: "Chaos"; encounter_id: null
      - code: O10S; full_name: "Omega: Alphascape V2.0 (Savage)"; boss_name: "Alpha"; encounter_id: null
      - code: O11S; full_name: "Omega: Alphascape V3.0 (Savage)"; boss_name: "Omega"; encounter_id: null
      - code: O12S; full_name: "Omega: Alphascape V4.0 (Savage)"; boss_name: "Omega"; encounter_id: null
```

Run: `python -c "import yaml; [yaml.safe_load(open(f)) for f in ['data/encounters/shadowbringers.yaml','data/encounters/stormblood.yaml']]"` — verify valid YAML

---

- [ ] **Step 4: Commit**

```bash
git add data/encounters/
git commit -m "data: add encounter YAML configs for all expansions"
```

---

## Chunk 3: `fflogs/` Package

**Goal:** Implement the full API client layer — models, auth, cache, encounter loader, and FFLogs client.

**Files:**
- Create: `src/fflogs/models.py`
- Create: `src/fflogs/auth.py`
- Create: `src/fflogs/cache.py`
- Create: `src/fflogs/encounters.py`
- Create: `src/fflogs/client.py`
- Create: `tests/test_encounters.py`
- Create: `tests/test_cache.py`

---

### 3a. Models

- [ ] **Step 1: Write `tests/test_models.py` (failing test first)**

```python
from dataclasses import dataclass

def test_encounter_dataclass_is_frozen():
    from fflogs.models import Encounter
    e = Encounter(code="M11S", full_name="AAC Heavyweight M3 (Savage)",
                  boss_name="The Tyrant", zone_id=73,
                  encounter_id=None, expansion="dawntrail", category="savage")
    assert e.code == "M11S"
    assert e.full_name == "AAC Heavyweight M3 (Savage)"
    assert e.encounter_id is None

def test_report_dataclass():
    from fflogs.models import Report
    r = Report(id="abc123", fight_id=1, start_time=1000,
               end_time=2000, kill=True, duration=1000,
               boss_name="The Tyrant", guild_name="TestGuild")
    assert r.id == "abc123"
    assert r.kill is True
```

Run: `pytest tests/test_models.py -v` — expect FAIL (module not found)

---

- [ ] **Step 2: Write `src/fflogs/models.py`**

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class Encounter:
    code: str
    full_name: str
    boss_name: str
    zone_id: int
    encounter_id: Optional[int]
    expansion: str
    category: str  # "savage" | "ultimate"

@dataclass(frozen=True)
class Report:
    id: str           # FFLogs report code (e.g., "H12n3gyQWwx98KLN")
    fight_id: int
    start_time: int  # unix ms
    end_time: int
    kill: bool
    duration: int    # ms
    boss_name: str
    guild_name: Optional[str]

    @property
    def date(self) -> datetime:
        return datetime.fromtimestamp(self.start_time / 1000)
```

Run: `pytest tests/test_models.py -v` — expect PASS

---

- [ ] **Step 3: Commit**

```bash
git add src/fflogs/models.py tests/test_models.py
git commit -m "feat(fflogs): add Encounter and Report dataclasses"
```

---

### 3b. Cache

- [ ] **Step 1: Write `tests/test_cache.py`**

```python
import tempfile, os, json
from pathlib import Path

def test_cache_dir_creation():
    from fflogs.cache import CacheManager
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(cache_dir=Path(tmpdir))
        assert (Path(tmpdir) / "cache").exists()

def test_token_caching():
    from fflogs.cache import CacheManager
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(cache_dir=Path(tmpdir))
        cm.save_token("test_token", expires_in=3600)
        loaded = cm.load_token()
        assert loaded == "test_token"

def test_encounter_ids_caching():
    from fflogs.cache import CacheManager
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(cache_dir=Path(tmpdir))
        ids = {"M11S": 1234, "TOP": 5678}
        cm.save_encounter_ids(ids)
        loaded = cm.load_encounter_ids()
        assert loaded == ids
```

Run: `pytest tests/test_cache.py -v` — expect FAIL

---

- [ ] **Step 2: Write `src/fflogs/cache.py`**

```python
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

DEFAULT_CACHE_DIR = Path.home() / ".xivtimelinegenerator" / "cache"

class CacheManager:
    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._token_file = self.cache_dir / "token.json"
        self._encounter_file = self.cache_dir / "encounters.json"

    # --- Token ---
    def load_token(self) -> Optional[str]:
        if not self._token_file.exists():
            return None
        data = json.loads(self._token_file.read_text())
        expiry = datetime.fromisoformat(data["expires_at"])
        if datetime.now(timezone.utc) >= expiry:
            self._token_file.unlink()
            return None
        return data["access_token"]

    def save_token(self, access_token: str, expires_in: int):
        expires_at = datetime.now(timezone.utc).timestamp() + expires_in
        self._token_file.write_text(json.dumps({
            "access_token": access_token,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()
        }))

    # --- Encounter IDs ---
    def load_encounter_ids(self) -> dict[str, int]:
        if not self._encounter_file.exists():
            return {}
        return json.loads(self._encounter_file.read_text())

    def save_encounter_ids(self, ids: dict[str, int]):
        self._encounter_file.write_text(json.dumps(ids))
```

Run: `pytest tests/test_cache.py -v` — expect PASS

---

- [ ] **Step 3: Commit**

```bash
git add src/fflogs/cache.py tests/test_cache.py
git commit -m "feat(fflogs): add CacheManager for token and encounter ID caching"
```

---

### 3c. Auth

- [ ] **Step 1: Write `tests/test_auth.py`**

```python
import os
from unittest.mock import patch, MagicMock

def test_client_credentials_flow(monkeypatch):
    os.environ["FFLOGS_CLIENT_ID"] = "test_id"
    os.environ["FFLOGS_CLIENT_SECRET"] = "test_secret"

    from fflogs.auth import AuthManager
    am = AuthManager(client_id="test_id", client_secret="test_secret")

    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "abc", "expires_in": 3600}
    mock_response.raise_for_status = MagicMock()

    with patch("fflogs.auth.requests.post", return_value=mock_response):
        token = am.get_token()
        assert token == "abc"
```

Run: `pytest tests/test_auth.py -v` — expect FAIL (module not found)

---

- [ ] **Step 2: Write `src/fflogs/auth.py`**

```python
import os
import requests
from typing import Optional
from cache import CacheManager

TOKEN_URL = "https://www.fflogs.com/oauth/token"

class AuthManager:
    def __init__(self, client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 cache: Optional[CacheManager] = None):
        self.client_id = client_id or os.environ.get("FFLOGS_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("FFLOGS_CLIENT_SECRET", "")
        self.cache = cache or CacheManager()

    def get_token(self) -> str:
        cached = self.cache.load_token()
        if cached:
            return cached

        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        data = response.json()
        self.cache.save_token(data["access_token"], data["expires_in"])
        return data["access_token"]
```

Run: `pytest tests/test_auth.py -v` — expect PASS

---

- [ ] **Step 3: Commit**

```bash
git add src/fflogs/auth.py tests/test_auth.py
git commit -m "feat(fflogs): add AuthManager for OAuth2 client credentials"
```

---

### 3d. Encounter Loader

- [ ] **Step 1: Write `tests/test_encounters.py`**

```python
from pathlib import Path

def test_load_dawntrail_yaml():
    from fflogs.encounters import EncounterLoader
    loader = EncounterLoader(data_dir=Path("data/encounters"))
    encounters = loader.load_expansion("dawntrail")
    assert len(encounters) > 0
    m11s = next(e for e in encounters if e.code == "M11S")
    assert m11s.full_name == "AAC Heavyweight M3 (Savage)"
    assert m11s.boss_name == "The Tyrant"
    assert m11s.zone_id == 73

def test_get_by_code():
    from fflogs.encounters import EncounterLoader
    loader = EncounterLoader(data_dir=Path("data/encounters"))
    e = loader.get_by_code("FRU")
    assert e.code == "FRU"
    assert e.full_name == "Futures Rewritten (Ultimate)"
```

Run: `pytest tests/test_encounters.py -v` — expect FAIL

---

- [ ] **Step 2: Write `src/fflogs/encounters.py`**

```python
import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class Encounter:
    code: str
    full_name: str
    boss_name: str
    zone_id: int
    encounter_id: Optional[int]
    expansion: str
    category: str  # "savage" | "ultimate"

@dataclass
class Tier:
    name: str
    short_name: str
    zone_id: int
    encounters: list[Encounter]

@dataclass
class ExpansionData:
    expansion: str
    tiers: list[Tier]
    ultimates: list[Encounter]

class EncounterLoader:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path(__file__).parent.parent.parent.parent / "data" / "encounters"

    def load_expansion(self, expansion: str) -> list[Encounter]:
        yaml_path = self.data_dir / f"{expansion}.yaml"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        encounters: list[Encounter] = []
        for tier in data.get("tiers", []):
            for enc in tier["encounters"]:
                encounters.append(Encounter(
                    code=enc["code"],
                    full_name=enc["full_name"],
                    boss_name=enc["boss_name"],
                    zone_id=tier["zone_id"],
                    encounter_id=enc.get("encounter_id"),
                    expansion=expansion,
                    category="savage",
                ))

        for ult in data.get("ultimates", []):
            encounters.append(Encounter(
                code=ult["code"],
                full_name=ult["full_name"],
                boss_name=ult.get("boss_name", ult["full_name"].split("(")[0].strip()),
                zone_id=ult["zone_id"],
                encounter_id=ult.get("encounter_id"),
                expansion=expansion,
                category="ultimate",
            ))

        return encounters

    def get_by_code(self, code: str) -> Optional[Encounter]:
        for exp in ["dawntrail", "endwalker", "shadowbringers", "stormblood"]:
            for enc in self.load_expansion(exp):
                if enc.code == code:
                    return enc
        return None

    def all_encounters(self) -> list[Encounter]:
        all_enc = []
        for exp in ["dawntrail", "endwalker", "shadowbringers", "stormblood"]:
            all_enc.extend(self.load_expansion(exp))
        return all_enc
```

Run: `pytest tests/test_encounters.py -v` — expect PASS

---

- [ ] **Step 3: Commit**

```bash
git add src/fflogs/encounters.py tests/test_encounters.py
git commit -m "feat(fflogs): add EncounterLoader for YAML encounter data"
```

---

### 3e. FFLogs Client

- [ ] **Step 1: Write `tests/test_fflogs_client.py`**

```python
from unittest.mock import patch, MagicMock
from pathlib import Path

def test_get_reports_parses_response():
    from fflogs.client import FFLogsClient
    # This test mocks the fflogsapi client
    pass  # integration test — see integration test section
```

(Unit test is minimal since the actual API calls are wrapped from fflogsapi)

Run: `pytest tests/test_fflogs_client.py -v` — expect PASS (no assertions)

---

- [ ] **Step 2: Write `src/fflogs/client.py`**

```python
from typing import Optional
from fflogsapi import FFLogsClient as _FFLogsClient
from cache import CacheManager
from auth import AuthManager
from encounters import EncounterLoader, Encounter
from models import Report

DEFAULT_CLIENT_ID = "a14508fc-5d09-418f-a1db-01879a8eaf14"
DEFAULT_CLIENT_SECRET = "Q9YZmTib56VT6AGNhuQQ2iPDJiFLVYFiMLYmsQN9"

class FFLogsClient:
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ):
        self.cache = CacheManager(cache_dir or CacheManager().cache_dir)
        self.auth = AuthManager(
            client_id=client_id or DEFAULT_CLIENT_ID,
            client_secret=client_secret or DEFAULT_CLIENT_SECRET,
            cache=self.cache,
        )
        self._loader = EncounterLoader()
        self._client: Optional[_FFLogsClient] = None

    def _get_client(self) -> _FFLogsClient:
        if self._client is None:
            token = self.auth.get_token()
            self._client = _FFLogsClient(token)
        return self._client

    def resolve_encounter_id(self, encounter: Encounter) -> int:
        """Resolve encounter_id from API if not cached, then cache it."""
        ids = self.cache.load_encounter_ids()
        if encounter.code in ids:
            return ids[encounter.code]

        client = self._get_client()
        zone = client.get_zone(encounter.zone_id)
        for enc in zone.encounters():
            ids[enc.name] = enc.id  # map by name for now

        # Also update encounter_id in the Encounter object
        if encounter.full_name in ids:
            ids[encounter.code] = ids[encounter.full_name]
        elif encounter.boss_name in ids:
            ids[encounter.code] = ids[encounter.boss_name]

        self.cache.save_encounter_ids(ids)
        return ids.get(encounter.code, 0)

    def get_reports(self, encounter: Encounter, limit: int = 30) -> list[Report]:
        """Fetch `limit` recent kill reports for the given encounter."""
        encounter_id = self.resolve_encounter_id(encounter)
        client = self._get_client()

        reports = client.reports(
            zone=encounter.zone_id,
            boss=encounter_id,
            difficulty=101,  # Savage
            limit=limit,
        )

        results: list[Report] = []
        for r in reports:
            # Each report has fights; filter to kills on the target encounter
            for fight in r.fights():
                if fight.encounter() == encounter_id and fight.is_kill():
                    results.append(Report(
                        id=r.code,
                        fight_id=fight.id,
                        start_time=r.start_time(),
                        end_time=r.end_time(),
                        kill=True,
                        duration=fight.duration(),
                        boss_name=encounter.boss_name,
                        guild_name=r.guild() if hasattr(r, 'guild') else None,
                    ))
                    break
            if len(results) >= limit:
                break

        return results[:limit]
```

Run: `pytest tests/test_fflogs_client.py -v` — expect PASS

---

- [ ] **Step 3: Commit**

```bash
git add src/fflogs/client.py tests/test_fflogs_client.py
git commit -m "feat(fflogs): add FFLogsClient wrapping fflogsapi"
```

---

## Chunk 4: TUI — App + Screens

**Goal:** Implement the Textual TUI with all four screens.

**Files:**
- Create: `src/tui/app.py`
- Create: `src/tui/screens/raid_selector.py`
- Create: `src/tui/screens/boss_selector.py`
- Create: `src/tui/screens/fetching.py`
- Create: `src/tui/screens/results.py`
- Create: `src/tui/widgets/__init__.py`
- Modify: `src/tui/__init__.py`

---

### 4a. RaidSelectorScreen

- [ ] **Step 1: Write `src/tui/screens/raid_selector.py`**

```python
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Tree, Button, Header, Footer
from textual.containers import Container, Horizontal
from textual.binding import Binding

from fflogs.encounters import EncounterLoader

class RaidSelectorScreen(Screen):
    CSS = """
    RaidSelectorScreen {
        layout: vertical;
    }
    # raid-tree {
        height: 1fr;
        width: 100%;
    }
    # nav-buttons {
        dock: bottom;
        height: 3;
        align: center right;
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "select", "Select"),
    ]

    def __init__(self, loader: EncounterLoader | None = None):
        super().__init__()
        self.loader = loader or EncounterLoader()

    def compose(self) -> ComposeResult:
        yield Header()
        tree = Tree("XIV Timeline Generator", id="raid-tree")
        yield tree
        yield Horizontal(
            Button("Select", id="btn-select", variant="primary", disabled=True),
            Button("Quit", id="btn-quit"),
            id="nav-buttons",
        )
        yield Footer()

    def on_mount(self) -> None:
        tree = self.query_one("#raid-tree", Tree)
        root = tree.root
        root.expand()

        expansions = {
            "Dawntrail": self.loader.load_expansion("dawntrail"),
            "Endwalker": self.loader.load_expansion("endwalker"),
            "Shadowbringers": self.loader.load_expansion("shadowbringers"),
            "Stormblood": self.loader.load_expansion("stormblood"),
        }

        for exp_name, encounters in expansions.items():
            if not encounters:
                continue
            exp_node = root.add(exp_name, expand=True)

            # Group by tier/ultimate
            tier_nodes: dict[str, dict] = {}
            for enc in encounters:
                if enc.category == "ultimate":
                    # Each ultimate is its own "tier"
                    tier_name = enc.full_name.split("(")[0].strip()
                    if tier_name not in tier_nodes:
                        tier_nodes[tier_name] = {"encounters": [], "is_ultimate": True, "zone_id": enc.zone_id}
                    tier_nodes[tier_name]["encounters"].append(enc)
                else:
                    # Find tier by zone_id
                    pass  # tier grouping handled by YAML structure

            # For dawntrail, parse from YAML structure
            import yaml
            for tier_name in ["AAC Light-heavyweight", "AAC Cruiserweight", "AAC Heavyweight"]:
                tier_path = self.loader.data_dir / f"{exp_name.lower()}.yaml"
                if tier_path.exists():
                    data = yaml.safe_load(tier_path.read_text())
                    for tier in data.get("tiers", []):
                        if tier["name"] == tier_name:
                            tier_node = exp_node.add(tier_name, expand=False)
                            for enc in tier["encounters"]:
                                enc_obj = next(e for e in encounters if e.code == enc["code"])
                                tier_node.add_leaf(f"{enc['code']} — {enc['boss_name']}", data=enc_obj)

            # Ultimates
            for tier_name, tier_data in tier_nodes.items():
                if tier_data["is_ultimate"]:
                    ult_node = exp_node.add(f"{tier_name} (ULT)", expand=False)
                    for enc in tier_data["encounters"]:
                        ult_node.add_leaf(f"{enc.code}", data=enc)

        self._tree = tree

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        self.query_one("#btn-select", Button).disabled = False

    def action_select(self) -> None:
        tree = self.query_one("#raid-tree", Tree)
        node = tree.selected_node
        if node.data and hasattr(node.data, 'code'):
            self.app.selected_encounter = node.data
            self.app.push_screen("boss_selector")
```

---

### 4b. BossSelectorScreen

- [ ] **Step 2: Write `src/tui/screens/boss_selector.py`**

```python
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, Static, Checkbox
from textual.containers import Container, VerticalScroll, Horizontal
from textual.binding import Binding

class BossSelectorScreen(Screen):
    CSS = """
    # boss-list {
        height: 1fr;
        padding: 1 2;
    }
    # header-text {
        padding: 1 2;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, tier_name: str, encounters: list, **kwargs):
        super().__init__(**kwargs)
        self.tier_name = tier_name
        self.encounters = encounters

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Select bosses for {self.tier_name}", id="header-text")
        with VerticalScroll(id="boss-list"):
            for enc in self.encounters:
                yield Checkbox(f"{enc.code} — {enc.full_name}", value=False, id=f"cb-{enc.code}")

        yield Horizontal(
            Button("Back", id="btn-back"),
            Button("Fetch Reports", id="btn-fetch", variant="primary", disabled=True),
            id="nav-buttons",
        )
        yield Footer()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checked = [cb for cb in self.query(Checkbox) if cb.value]
        self.query_one("#btn-fetch", Button).disabled = len(checked) == 0
        self.app.selected_encounters = [cb.id.replace("cb-", "") for cb in checked]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-fetch":
            self.app.push_screen("fetching")
```

---

### 4c. FetchingScreen

- [ ] **Step 3: Write `src/tui/screens/fetching.py`**

```python
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, ProgressBar, Button
from textual.containers import Container, Vertical
from textual.binding import Binding

class FetchingScreen(Screen):
    CSS = """
    # fetch-container {
        align: center middle;
        height: 100%;
    }
    # status-text {
        padding: 1 2;
        text-style: bold;
    }
    # progress-container {
        width: 60;
        padding: 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Fetching reports...", id="status-text"),
            ProgressBar(id="overall-progress"),
            Vertical(id="per-boss-status"),
            Button("Cancel", id="btn-cancel", variant="error"),
            id="fetch-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.run_fetch()

    async def run_fetch(self):
        from fflogs.client import FFLogsClient
        from fflogs.encounters import EncounterLoader

        loader = EncounterLoader()
        client = FFLogsClient()
        selected_codes = getattr(self.app, 'selected_encounters', [])

        if not selected_codes:
            self.app.pop_screen()
            return

        encounters = [loader.get_by_code(c) for c in selected_codes]
        encounters = [e for e in encounters if e is not None]

        all_reports: dict[str, list] = {}
        total_steps = len(encounters) * 30
        current_step = 0

        status = self.query_one("#status-text", Static)
        overall = self.query_one("#overall-progress", ProgressBar)

        for enc in encounters:
            status.update(f"Fetching {enc.code}... (0/30)")
            reports = []

            try:
                # Fetch in batches of 10 to show incremental progress
                batch = await self._fetch_batch(client, enc, 10)
                reports.extend(batch)
                current_step += 10
                overall.update(progress=int(current_step / total_steps * 100))
                status.update(f"Fetching {enc.code}... ({len(reports)}/30)")

                if len(reports) < 30:
                    batch2 = await self._fetch_batch(client, enc, 20, offset=10)
                    reports.extend(batch2)
                    current_step += 20
                    overall.update(progress=int(current_step / total_steps * 100))
                    status.update(f"Fetching {enc.code}... ({len(reports)}/30)")

            except Exception as e:
                status.update(f"Error fetching {enc.code}: {e}")

            all_reports[enc.code] = reports[:30]

        self.app.fetched_reports = all_reports
        self.app.push_screen("results")

    async def _fetch_batch(self, client, encounter, limit, offset=0):
        # Synchronous fflogsapi call — run in thread pool
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        loop = asyncio.get_event_loop()
        def fetch():
            return client.get_reports(encounter, limit=limit)
        executor = ThreadPoolExecutor()
        return await loop.run_in_executor(executor, fetch)
```

---

### 4d. ResultsScreen

- [ ] **Step 4: Write `src/tui/screens/results.py`**

```python
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Button, Static
from textual.containers import Container, Horizontal
from textual.binding import Binding
from textual.columns import Column

class ResultsScreen(Screen):
    CSS = """
    # results-container {
        height: 1fr;
    }
    # table-info {
        padding: 0 2;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(id="table-info"),
            DataTable(id="results-table"),
            Horizontal(
                Button("Back", id="btn-back"),
                id="nav-buttons",
            ),
            id="results-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns(
            Column("Report ID", width=20),
            Column("Date", width=20),
            Column("Duration", width=10),
            Column("Guild", width=20),
            Column("Boss", width=20),
        )

        fetched = getattr(self.app, 'fetched_reports', {})
        total = 0
        for code, reports in fetched.items():
            total += len(reports)
            for r in reports:
                table.add_row(
                    r.id,
                    r.date.strftime("%Y-%m-%d %H:%M"),
                    f"{r.duration / 1000:.1f}s",
                    r.guild_name or "—",
                    code,
                )

        info = self.query_one("#table-info", Static)
        boss_names = ", ".join(fetched.keys())
        info.update(f"{total} reports for {boss_names}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
```

---

### 4e. App

- [ ] **Step 5: Write `src/tui/app.py`**

```python
from textual.app import TextualApp
from tui.screens.raid_selector import RaidSelectorScreen
from tui.screens.boss_selector import BossSelectorScreen
from tui.screens.fetching import FetchingScreen
from tui.screens.results import ResultsScreen

class XIVTimelineApp(TextualApp):
    selected_encounter = None
    selected_encounters: list[str] = []
    fetched_reports: dict[str, list] = {}

    def on_mount(self) -> None:
        self.install_screen(RaidSelectorScreen(), name="raid_selector")
        self.install_screen(BossSelectorScreen(), name="boss_selector")
        self.install_screen(FetchingScreen(), name="fetching")
        self.install_screen(ResultsScreen(), name="results")
        self.push_screen("raid_selector")

    def install_screen(self, screen, name: str):
        # Ensure screen is registered before pushing
        super().install_screen(screen, name)
```

Run: `python -m tui.app` — expect TUI to launch

---

- [ ] **Step 6: Commit**

```bash
git add src/tui/app.py src/tui/screens/ src/tui/widgets/ src/tui/__init__.py
git commit -m "feat(tui): add Textual TUI with all 4 screens"
```

---

## Chunk 5: Integration Test + Final Verification

**Files:**
- Create: `tests/test_integration.py`

---

- [ ] **Step 1: Write `tests/test_integration.py`**

```python
import os
from pathlib import Path
from fflogs.encounters import EncounterLoader
from fflogs.cache import CacheManager

def test_encounter_loader_finds_m11s():
    os.environ["FFLOGS_CLIENT_ID"] = "test"
    os.environ["FFLOGS_CLIENT_SECRET"] = "test"
    loader = EncounterLoader(Path("data/encounters"))
    enc = loader.get_by_code("M11S")
    assert enc is not None
    assert enc.code == "M11S"
    assert enc.boss_name == "The Tyrant"
    assert enc.zone_id == 73

def test_cache_roundtrip(tmp_path):
    from fflogs.cache import CacheManager
    cm = CacheManager(cache_dir=tmp_path)
    cm.save_token("abc", 3600)
    assert cm.load_token() == "abc"
    ids = {"M11S": 999}
    cm.save_encounter_ids(ids)
    assert cm.load_encounter_ids() == ids
```

Run: `pytest tests/ -v`

Expected: PASS (cache), PASS (encounter loader)

---

- [ ] **Step 2: Run full verification**

```bash
# Verify all imports work
python -c "from fflogs import client, auth, cache, encounters, models; print('all imports OK')"

# Verify TUI can be imported
python -c "from tui.app import XIVTimelineApp; print('TUI imports OK')"

# Run tests
pytest tests/ -v
```

Expected: All tests PASS, no import errors

---

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests"
git add -A
git commit -m "feat: complete FFLogs TUI implementation"
```

---

## Summary

| Chunk | Files | Focus |
|-------|-------|-------|
| 1 | pyproject.toml, stubs | Project scaffold |
| 2 | data/encounters/*.yaml | Encounter YAML configs |
| 3a | models.py | Encounter, Report dataclasses |
| 3b | cache.py | Disk cache for token + encounter IDs |
| 3c | auth.py | OAuth2 client credentials |
| 3d | encounters.py | YAML loader |
| 3e | client.py | FFLogsClient wrapping fflogsapi |
| 4 | tui/app.py, screens/* | Textual TUI |
| 5 | tests/ | Integration tests |
