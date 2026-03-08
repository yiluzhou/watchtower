from fastapi import APIRouter
from pydantic import BaseModel

from ..config import load_config, save_config, geocode
from ..models import AppConfig
from ..services.intel import (
    resolve_local_model_name,
    schedule_local_provider_warmup,
    stop_local_provider_model,
)

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigResponse(BaseModel):
    llm_provider: str
    llm_api_key_set: bool
    llm_model: str
    city: str
    country: str
    latitude: float
    longitude: float
    temp_unit: str
    refresh_seconds: int
    crypto_pairs: list[str]
    brief_cache_minutes: int


@router.get("", response_model=ConfigResponse)
async def get_config():
    cfg = load_config()
    return ConfigResponse(
        llm_provider=cfg.llm_provider,
        llm_api_key_set=bool(cfg.llm_api_key),
        llm_model=cfg.llm_model,
        city=cfg.location.city,
        country=cfg.location.country,
        latitude=cfg.location.latitude,
        longitude=cfg.location.longitude,
        temp_unit=cfg.temp_unit,
        refresh_seconds=cfg.refresh_seconds,
        crypto_pairs=cfg.crypto_pairs,
        brief_cache_minutes=cfg.brief_cache_minutes,
    )


class ConfigUpdate(BaseModel):
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    city: str | None = None
    country: str | None = None
    temp_unit: str | None = None
    refresh_seconds: int | None = None
    crypto_pairs: list[str] | None = None
    brief_cache_minutes: int | None = None


@router.post("", response_model=ConfigResponse)
async def update_config(update: ConfigUpdate):
    cfg = load_config()
    prev_provider = cfg.llm_provider
    prev_local_model = resolve_local_model_name(cfg.llm_model) if prev_provider == "local" else ""

    if update.llm_provider is not None:
        cfg.llm_provider = update.llm_provider
    if update.llm_api_key is not None:
        cfg.llm_api_key = update.llm_api_key
    if update.llm_model is not None:
        cfg.llm_model = update.llm_model
    if update.temp_unit is not None:
        cfg.temp_unit = update.temp_unit
    if update.refresh_seconds is not None:
        cfg.refresh_seconds = update.refresh_seconds
    if update.crypto_pairs is not None:
        cfg.crypto_pairs = update.crypto_pairs
    if update.brief_cache_minutes is not None:
        cfg.brief_cache_minutes = update.brief_cache_minutes

    if update.city is not None or update.country is not None:
        city = update.city or cfg.location.city
        country = update.country or cfg.location.country
        if city and country:
            lat, lon = await geocode(city, country)
            cfg.location.city = city
            cfg.location.country = country
            cfg.location.latitude = lat
            cfg.location.longitude = lon

    save_config(cfg)

    next_local_model = resolve_local_model_name(cfg.llm_model) if cfg.llm_provider == "local" else ""
    if prev_provider == "local" and prev_local_model != next_local_model:
        await stop_local_provider_model(prev_local_model)

    if cfg.llm_provider == "local":
        # Kick off local provider setup right after saving settings.
        schedule_local_provider_warmup(cfg.llm_model)

    return ConfigResponse(
        llm_provider=cfg.llm_provider,
        llm_api_key_set=bool(cfg.llm_api_key),
        llm_model=cfg.llm_model,
        city=cfg.location.city,
        country=cfg.location.country,
        latitude=cfg.location.latitude,
        longitude=cfg.location.longitude,
        temp_unit=cfg.temp_unit,
        refresh_seconds=cfg.refresh_seconds,
        crypto_pairs=cfg.crypto_pairs,
        brief_cache_minutes=cfg.brief_cache_minutes,
    )
