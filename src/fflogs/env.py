"""Project-local environment loading helpers."""

from __future__ import annotations

import os
from pathlib import Path

_HAS_LOADED_PROJECT_ENV = False


def load_project_env() -> Path | None:
    """Load a local .env file into os.environ once without overriding existing values."""
    global _HAS_LOADED_PROJECT_ENV
    if _HAS_LOADED_PROJECT_ENV:
        return None
    _HAS_LOADED_PROJECT_ENV = True

    if _is_truthy(os.environ.get("XIV_TIMELINE_SKIP_DOTENV")):
        return None

    env_path = _resolve_env_path()
    if env_path is None or not env_path.exists():
        return None

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _strip_wrapping_quotes(value.strip())

    return env_path


def _resolve_env_path() -> Path | None:
    explicit = os.environ.get("XIV_TIMELINE_DOTENV_PATH")
    if explicit:
        return Path(explicit).expanduser().resolve()

    current = Path.cwd().resolve()
    for candidate_dir in (current, *current.parents):
        candidate = candidate_dir / ".env"
        if candidate.exists():
            return candidate
    return None


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}
