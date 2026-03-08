from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..models import WeatherConditions, DayForecast

WMO_CODES: dict[int, tuple[str, str, str, str]] = {
    # code: (day_icon, day_desc, night_icon, night_desc)
    0: ("\u2600\ufe0f", "Clear sky", "\U0001f319", "Clear night"),
    1: ("\U0001f324\ufe0f", "Mainly clear", "\U0001f324\ufe0f", "Mainly clear"),
    2: ("\u26c5", "Partly cloudy", "\u26c5", "Partly cloudy"),
    3: ("\u2601\ufe0f", "Overcast", "\u2601\ufe0f", "Overcast"),
}


def _wmo_code_to_emoji(code: int, is_day: bool) -> tuple[str, str]:
    if code in WMO_CODES:
        entry = WMO_CODES[code]
        if is_day:
            return entry[0], entry[1]
        return entry[2], entry[3]

    if 45 <= code <= 48:
        return "\U0001f32b\ufe0f", "Fog"
    if 51 <= code <= 57:
        return "\U0001f326\ufe0f", "Drizzle"
    if 61 <= code <= 67:
        return "\U0001f327\ufe0f", "Rain"
    if 71 <= code <= 77:
        return "\u2744\ufe0f", "Snow"
    if 80 <= code <= 82:
        return "\U0001f326\ufe0f", "Rain showers"
    if code == 95:
        return "\u26c8\ufe0f", "Thunderstorm"
    if 96 <= code <= 99:
        return "\u26c8\ufe0f", "Thunderstorm with hail"
    return "\U0001f321\ufe0f", "Unknown"


def _wind_direction_str(deg: int) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = ((deg + 22) % 360) // 45
    return dirs[idx] if idx < len(dirs) else "N"


async def fetch_weather(lat: float, lon: float, city: str) -> tuple[WeatherConditions, list[DayForecast]]:
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat:.4f}&longitude={lon:.4f}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
        f"weather_code,wind_speed_10m,wind_direction_10m,uv_index,visibility"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"
        f"&timezone=auto&forecast_days=10"
    )

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    current = data["current"]
    is_day = current.get("is_day", 1) == 1
    icon, desc = _wmo_code_to_emoji(current.get("weather_code", 0), is_day)

    conditions = WeatherConditions(
        city=city,
        temp_c=current.get("temperature_2m", 0),
        feels_like_c=current.get("apparent_temperature", 0),
        humidity=current.get("relative_humidity_2m", 0),
        wind_speed_kmh=current.get("wind_speed_10m", 0),
        wind_direction=current.get("wind_direction_10m", 0),
        description=desc,
        icon=icon,
        visibility=current.get("visibility", 0),
        uv_index=current.get("uv_index", 0),
        is_day=is_day,
        updated_at=datetime.now(timezone.utc),
    )

    daily = data.get("daily", {})
    times = daily.get("time", [])
    codes = daily.get("weather_code", [])
    maxs = daily.get("temperature_2m_max", [])
    mins = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])

    forecasts: list[DayForecast] = []
    for i, date_str in enumerate(times):
        if i >= len(codes):
            break
        ico, dsc = _wmo_code_to_emoji(codes[i], True)
        rain = precip[i] if i < len(precip) else 0.0
        forecasts.append(DayForecast(
            date=date_str,
            max_temp_c=maxs[i] if i < len(maxs) else 0,
            min_temp_c=mins[i] if i < len(mins) else 0,
            rain_mm=rain,
            icon=ico,
            desc=dsc,
        ))

    return conditions, forecasts
