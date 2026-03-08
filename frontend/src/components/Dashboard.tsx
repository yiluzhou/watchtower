import { useState } from 'react'
import { useWeather, useMarkets } from '../hooks/useApi'
import WeatherPanel from './WeatherPanel'
import BriefPanel from './BriefPanel'
import MarketsPanel from './MarketsPanel'
import type { Brief } from '../types'

interface Props {
  refetchInterval: number
}

export default function Dashboard({ refetchInterval }: Props) {
  const weather = useWeather(refetchInterval)
  const markets = useMarkets(refetchInterval)
  const [brief, setBrief] = useState<Brief | null>(null)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-4">
      {/* Top-left: Weather */}
      <div>
        {weather.isLoading && (
          <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4">
            <div className="text-[#8b949e] text-sm animate-pulse">Loading weather...</div>
          </div>
        )}
        {weather.data && (
          <WeatherPanel conditions={weather.data.conditions} forecast={weather.data.forecast} />
        )}
        {weather.isError && (
          <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4 text-[#f85149] text-sm">
            Weather error: {weather.error.message}
          </div>
        )}
      </div>

      {/* Top-right: Brief */}
      <div>
        <BriefPanel brief={brief} onBriefLoaded={setBrief} />
      </div>

      {/* Bottom: Markets (full width) */}
      <div className="lg:col-span-2">
        <MarketsPanel data={markets.data} isLoading={markets.isLoading} />
      </div>
    </div>
  )
}
