from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import httpx
import yaml

from .models import AppConfig, Location

CONFIG_DIR = Path.home() / ".config" / "watchtower"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def config_exists() -> bool:
    return CONFIG_FILE.is_file()


def load_config() -> AppConfig:
    if not config_exists():
        return AppConfig()

    with open(CONFIG_FILE) as f:
        data = yaml.safe_load(f) or {}

    cfg = AppConfig(
        llm_provider=data.get("llm_provider", "groq"),
        llm_api_key=data.get("llm_api_key", ""),
        llm_model=data.get("llm_model", ""),
        temp_unit=data.get("temp_unit", "celsius"),
        refresh_seconds=data.get("refresh_seconds", 120) or 120,
        crypto_pairs=data.get("crypto_pairs") or ["bitcoin", "ethereum", "dogecoin", "usd-coin"],
        brief_cache_minutes=data.get("brief_cache_minutes", 60) or 60,
    )

    loc = data.get("location", {})
    if loc:
        cfg.location = Location(
            city=loc.get("city", ""),
            country=loc.get("country", ""),
            latitude=loc.get("latitude", 0.0),
            longitude=loc.get("longitude", 0.0),
        )

    env_key = os.environ.get("LLM_API_KEY")
    if env_key:
        cfg.llm_api_key = env_key

    return cfg


def save_config(cfg: AppConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "llm_provider": cfg.llm_provider,
        "llm_api_key": cfg.llm_api_key,
        "llm_model": cfg.llm_model,
        "location": {
            "city": cfg.location.city,
            "country": cfg.location.country,
            "latitude": cfg.location.latitude,
            "longitude": cfg.location.longitude,
        },
        "temp_unit": cfg.temp_unit,
        "refresh_seconds": cfg.refresh_seconds,
        "crypto_pairs": cfg.crypto_pairs,
        "brief_cache_minutes": cfg.brief_cache_minutes,
    }
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


async def geocode(city: str, country_code: str) -> tuple[float, float]:
    url = (
        f"https://geocoding-api.open-meteo.com/v1/search"
        f"?name={quote(city)}&country={country_code}&count=1&language=en&format=json"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    if not results:
        raise ValueError(f"City not found: {city}, {country_code}")

    return results[0]["latitude"], results[0]["longitude"]
