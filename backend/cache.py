from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import Brief, LocalBrief, CountryRisk

CACHE_DIR = Path.home() / ".cache" / "watchtower"


def _ensure_cache_dir() -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def load_cached_brief(max_age_minutes: int) -> Brief | None:
    path = _ensure_cache_dir() / "brief.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    generated_at = datetime.fromisoformat(data["generated_at"])
    if max_age_minutes > 0 and datetime.now(timezone.utc) - generated_at > timedelta(minutes=max_age_minutes):
        return None

    summary = (data.get("summary", "") or "").strip()
    if not summary:
        return None

    return Brief(
        summary=summary,
        key_threats=data.get("key_threats", []),
        country_risks=[CountryRisk(**cr) for cr in data.get("country_risks", [])],
        generated_at=generated_at,
        model=data.get("model", ""),
    )


def save_cached_brief(brief: Brief) -> None:
    try:
        path = _ensure_cache_dir() / "brief.json"
        data = brief.model_dump(mode="json")
        tmp = str(path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, str(path))
    except OSError:
        pass


def load_cached_local_brief(max_age_minutes: int) -> LocalBrief | None:
    path = _ensure_cache_dir() / "local_brief.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    generated_at = datetime.fromisoformat(data["generated_at"])
    if max_age_minutes > 0 and datetime.now(timezone.utc) - generated_at > timedelta(minutes=max_age_minutes):
        return None

    summary = (data.get("summary", "") or "").strip()
    if not summary:
        return None

    return LocalBrief(
        summary=summary,
        generated_at=generated_at,
        model=data.get("model", ""),
    )


def save_cached_local_brief(brief: LocalBrief) -> None:
    try:
        path = _ensure_cache_dir() / "local_brief.json"
        data = brief.model_dump(mode="json")
        tmp = str(path) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp, str(path))
    except OSError:
        pass
