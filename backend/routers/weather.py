from fastapi import APIRouter, HTTPException

from ..config import load_config
from ..models import WeatherResponse
from ..services.weather import fetch_weather

router = APIRouter(prefix="/api/weather", tags=["weather"])


@router.get("", response_model=WeatherResponse)
async def get_weather():
    cfg = load_config()
    if not cfg.location.latitude and not cfg.location.longitude:
        raise HTTPException(status_code=400, detail="Location not configured")
    conditions, forecast = await fetch_weather(
        cfg.location.latitude, cfg.location.longitude, cfg.location.city,
    )
    return WeatherResponse(conditions=conditions, forecast=forecast)
