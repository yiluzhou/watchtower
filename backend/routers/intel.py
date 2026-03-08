from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from ..cache import (
    load_cached_brief, save_cached_brief,
    load_cached_local_brief, save_cached_local_brief,
)
from ..config import load_config
from ..models import Brief, LocalBrief, LocalCapabilitiesResponse
from ..services.feeds import fetch_global_news, fetch_local_news
from ..services.intel import generate_brief, generate_local_brief, get_local_capabilities
from ..services.weather import fetch_weather

router = APIRouter(prefix="/api/intel", tags=["intel"])


class BriefRequest(BaseModel):
    force_refresh: bool = False


@router.get("/local-capabilities", response_model=LocalCapabilitiesResponse)
async def local_capabilities():
    return await get_local_capabilities()


@router.post("/brief", response_model=Brief)
async def get_brief(req: BriefRequest = BriefRequest()):
    cfg = load_config()

    if not req.force_refresh:
        cached = load_cached_brief(cfg.brief_cache_minutes)
        if cached:
            return cached

    try:
        items = await fetch_global_news()
        brief = await generate_brief(
            cfg.llm_provider, cfg.llm_api_key, cfg.llm_model, items,
        )
    except Exception as e:
        if cfg.llm_provider == "local":
            err = str(e)
            summary = (
                "Local Ollama setup is still in progress. "
                "Watchtower will auto-start Ollama and pull the selected model. "
                "Try Refresh again shortly."
            )
            err_l = err.lower()
            if "manual import required" in err_l or "ollama create" in err_l:
                summary = err
            if "automatic installation failed" in err_l or "automatic installation is unavailable" in err_l:
                summary = (
                    "Watchtower could not auto-install Ollama on this machine. "
                    "Install from https://ollama.com/download, then click Refresh."
                )
            elif "not installed" in err_l:
                summary = (
                    "Ollama is not installed on this machine. "
                    "Install from https://ollama.com/download, then click Refresh."
                )
            return Brief(
                summary=summary,
                generated_at=datetime.now(timezone.utc),
                model="local-setup",
            )
        return Brief(
            summary=f"Error generating brief: {e}",
            generated_at=datetime.now(timezone.utc),
            model="error",
        )

    save_cached_brief(brief)
    return brief


@router.post("/local-brief", response_model=LocalBrief)
async def get_local_brief(req: BriefRequest = BriefRequest()):
    cfg = load_config()

    if not req.force_refresh:
        cached = load_cached_local_brief(cfg.brief_cache_minutes)
        if cached:
            return cached

    try:
        items = await fetch_local_news(cfg.location.city, cfg.location.country)
        conditions = None
        forecast = []
        if cfg.location.latitude or cfg.location.longitude:
            try:
                conditions, forecast = await fetch_weather(
                    cfg.location.latitude, cfg.location.longitude, cfg.location.city,
                )
            except Exception:
                pass

        brief = await generate_local_brief(
            cfg.llm_provider, cfg.llm_api_key, cfg.llm_model,
            cfg.location.city, items, conditions, forecast,
        )
    except Exception as e:
        if cfg.llm_provider == "local":
            err = str(e)
            summary = (
                "Local Ollama setup is still in progress. "
                "Watchtower will auto-start Ollama and pull the selected model. "
                "Try Refresh again shortly."
            )
            err_l = err.lower()
            if "manual import required" in err_l or "ollama create" in err_l:
                summary = err
            if "automatic installation failed" in err_l or "automatic installation is unavailable" in err_l:
                summary = (
                    "Watchtower could not auto-install Ollama on this machine. "
                    "Install from https://ollama.com/download, then click Refresh."
                )
            elif "not installed" in err_l:
                summary = (
                    "Ollama is not installed on this machine. "
                    "Install from https://ollama.com/download, then click Refresh."
                )
            return LocalBrief(
                summary=summary,
                generated_at=datetime.now(timezone.utc),
                model="local-setup",
            )
        return LocalBrief(
            summary=f"Error generating local brief: {e}",
            generated_at=datetime.now(timezone.utc),
            model="error",
        )

    save_cached_local_brief(brief)
    return brief
