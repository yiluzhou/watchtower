import type { WeatherConditions, DayForecast } from '../types'

const WIND_DIRS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
function windDir(deg: number) {
  return WIND_DIRS[Math.floor(((deg + 22) % 360) / 45)] || 'N'
}

interface Props {
  conditions: WeatherConditions
  forecast: DayForecast[]
  compact?: boolean
}

export default function WeatherPanel({ conditions: c, forecast, compact }: Props) {
  return (
    <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4">
      <h3 className="text-[#d29922] font-semibold mb-3 text-sm uppercase tracking-wider">
        Weather — {c.city}
      </h3>
      <div className="flex items-center gap-4 mb-3">
        <span className="text-4xl">{c.icon}</span>
        <div>
          <div className="text-2xl font-bold">{c.temp_c.toFixed(1)}°C</div>
          <div className="text-[#8b949e] text-sm">Feels like {c.feels_like_c.toFixed(1)}°C</div>
        </div>
        <div className="text-[#8b949e] text-sm ml-auto">
          <div>{c.description}</div>
          <div>💧 {c.humidity}% | 💨 {c.wind_speed_kmh.toFixed(0)} km/h {windDir(c.wind_direction)}</div>
          <div>UV: {c.uv_index.toFixed(0)}</div>
        </div>
      </div>
      {!compact && (
        <div className="grid grid-cols-5 gap-1 mt-3 text-xs">
          {forecast.slice(0, 5).map((f) => (
            <div key={f.date} className="text-center p-2 rounded bg-[#0d1117]">
              <div className="text-[#8b949e]">{new Date(f.date).toLocaleDateString('en', { weekday: 'short' })}</div>
              <div className="text-lg my-1">{f.icon}</div>
              <div className="font-semibold">{f.max_temp_c.toFixed(0)}°</div>
              <div className="text-[#8b949e]">{f.min_temp_c.toFixed(0)}°</div>
              {f.rain_mm > 0 && <div className="text-[#58a6ff]">{f.rain_mm.toFixed(1)}mm</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
