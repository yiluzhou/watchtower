from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel


class ThreatLevel(IntEnum):
    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class NewsItem(BaseModel):
    title: str
    source: str
    published: datetime
    url: str = ""
    threat_level: ThreatLevel = ThreatLevel.INFO
    category: str = "general"
    is_local: bool = False


class CryptoPrice(BaseModel):
    id: str
    symbol: str
    name: str
    price_usd: float
    change_24h: float
    market_cap_usd: float
    volume_24h_usd: float
    last_updated: datetime | None = None


class StockIndex(BaseModel):
    symbol: str
    name: str
    price: float
    prev_close: float
    change_pct: float


class Commodity(BaseModel):
    symbol: str
    name: str
    price: float
    prev_close: float
    unit: str
    change_pct: float


class PredictionMarket(BaseModel):
    title: str
    probability: float
    volume: float
    category: str
    end_date: str
    slug: str


class CountryRisk(BaseModel):
    country: str
    score: int
    reason: str


class Brief(BaseModel):
    summary: str
    key_threats: list[str] = []
    country_risks: list[CountryRisk] = []
    generated_at: datetime
    model: str


class LocalBrief(BaseModel):
    summary: str
    generated_at: datetime
    model: str


class Location(BaseModel):
    city: str = ""
    country: str = ""
    latitude: float = 0.0
    longitude: float = 0.0


class AppConfig(BaseModel):
    llm_provider: str = "groq"
    llm_api_key: str = ""
    llm_model: str = ""
    location: Location = Location()
    temp_unit: str = "celsius"
    refresh_seconds: int = 120
    crypto_pairs: list[str] = ["bitcoin", "ethereum", "dogecoin", "usd-coin"]
    brief_cache_minutes: int = 60


class WeatherConditions(BaseModel):
    city: str
    temp_c: float
    feels_like_c: float
    humidity: int
    wind_speed_kmh: float
    wind_direction: int
    description: str
    icon: str
    visibility: float
    uv_index: float
    is_day: bool
    updated_at: datetime


class DayForecast(BaseModel):
    date: str
    max_temp_c: float
    min_temp_c: float
    rain_mm: float
    icon: str
    desc: str


class WeatherResponse(BaseModel):
    conditions: WeatherConditions
    forecast: list[DayForecast]


class MarketsResponse(BaseModel):
    crypto: list[CryptoPrice] = []
    stocks: list[StockIndex] = []
    commodities: list[Commodity] = []
    polymarket: list[PredictionMarket] = []
    errors: list[str] = []


class LocalGpuInfo(BaseModel):
    name: str = "Unknown"
    driver_version: str = ""
    total_vram_gb: float = 0.0
    free_vram_gb: float = 0.0
    detection: str = "unknown"


class LocalOllamaStatus(BaseModel):
    installed: bool = False
    running: bool = False
    binary_path: str = ""
    installed_models: list[str] = []


class LocalModelOption(BaseModel):
    name: str
    label: str
    family: str
    params_b: float
    est_vram_gb: float
    focus: str
    keywords: list[str]
    installed: bool = False
    fit: str = "unknown"
    auto_pull: bool = True
    install_hint: str = ""


class LocalModelRecommendations(BaseModel):
    best_reasoning: str = ""
    best_speed: str = ""
    best_overall: str = ""
    qwen35_27b_can_run: bool = False
    qwen35_27b_note: str = ""


class LocalCapabilitiesResponse(BaseModel):
    gpu: LocalGpuInfo
    ollama: LocalOllamaStatus
    recommendations: LocalModelRecommendations
    models: list[LocalModelOption]
    generated_at: datetime
