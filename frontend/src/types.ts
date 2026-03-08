export type ThreatLevel = 0 | 1 | 2 | 3 | 4

export const THREAT_LABELS: Record<ThreatLevel, string> = {
  0: 'INFO',
  1: 'LOW',
  2: 'MEDIUM',
  3: 'HIGH',
  4: 'CRITICAL',
}

export const THREAT_COLORS: Record<ThreatLevel, string> = {
  0: 'bg-gray-700',
  1: 'bg-green-900',
  2: 'bg-blue-900',
  3: 'bg-orange-900',
  4: 'bg-red-900',
}

export interface NewsItem {
  title: string
  source: string
  published: string
  url: string
  threat_level: ThreatLevel
  category: string
  is_local: boolean
}

export interface CryptoPrice {
  id: string
  symbol: string
  name: string
  price_usd: number
  change_24h: number
  market_cap_usd: number
  volume_24h_usd: number
  last_updated: string | null
}

export interface StockIndex {
  symbol: string
  name: string
  price: number
  prev_close: number
  change_pct: number
}

export interface Commodity {
  symbol: string
  name: string
  price: number
  prev_close: number
  unit: string
  change_pct: number
}

export interface PredictionMarket {
  title: string
  probability: number
  volume: number
  category: string
  end_date: string
  slug: string
}

export interface CountryRisk {
  country: string
  score: number
  reason: string
}

export interface Brief {
  summary: string
  key_threats: string[]
  country_risks: CountryRisk[]
  generated_at: string
  model: string
}

export interface LocalBrief {
  summary: string
  generated_at: string
  model: string
}

export interface WeatherConditions {
  city: string
  temp_c: number
  feels_like_c: number
  humidity: number
  wind_speed_kmh: number
  wind_direction: number
  description: string
  icon: string
  visibility: number
  uv_index: number
  is_day: boolean
  updated_at: string
}

export interface DayForecast {
  date: string
  max_temp_c: number
  min_temp_c: number
  rain_mm: number
  icon: string
  desc: string
}

export interface WeatherResponse {
  conditions: WeatherConditions
  forecast: DayForecast[]
}

export interface MarketsResponse {
  crypto: CryptoPrice[]
  stocks: StockIndex[]
  commodities: Commodity[]
  polymarket: PredictionMarket[]
  errors: string[]
}

export interface ConfigResponse {
  llm_provider: string
  llm_api_key_set: boolean
  llm_model: string
  city: string
  country: string
  latitude: number
  longitude: number
  temp_unit: string
  refresh_seconds: number
  crypto_pairs: string[]
  brief_cache_minutes: number
}

export interface LocalGpuInfo {
  name: string
  driver_version: string
  total_vram_gb: number
  free_vram_gb: number
  detection: string
}

export interface LocalOllamaStatus {
  installed: boolean
  running: boolean
  binary_path: string
  installed_models: string[]
}

export interface LocalModelOption {
  name: string
  label: string
  family: string
  params_b: number
  est_vram_gb: number
  focus: string
  keywords: string[]
  installed: boolean
  fit: string
  auto_pull: boolean
  install_hint: string
}

export interface LocalModelRecommendations {
  best_reasoning: string
  best_speed: string
  best_overall: string
  qwen35_27b_can_run: boolean
  qwen35_27b_note: string
}

export interface LocalCapabilitiesResponse {
  gpu: LocalGpuInfo
  ollama: LocalOllamaStatus
  recommendations: LocalModelRecommendations
  models: LocalModelOption[]
  generated_at: string
}
