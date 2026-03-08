import { useState } from 'react'
import { useLocalNews, useWeather, useLocalBrief } from '../hooks/useApi'
import WeatherPanel from './WeatherPanel'
import type { LocalBrief } from '../types'

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

interface Props {
  refetchInterval: number
}

export default function LocalTab({ refetchInterval }: Props) {
  const { data: news, isLoading: newsLoading } = useLocalNews(refetchInterval)
  const { data: weather } = useWeather(refetchInterval)
  const briefMutation = useLocalBrief()
  const [localBrief, setLocalBrief] = useState<LocalBrief | null>(null)

  const handleBrief = (force: boolean) => {
    briefMutation.mutate({ force_refresh: force }, { onSuccess: (data) => setLocalBrief(data) })
  }

  return (
    <div className="p-4 space-y-4">
      {/* Weather */}
      {weather && (
        <WeatherPanel conditions={weather.conditions} forecast={weather.forecast} />
      )}

      {/* Local Brief */}
      <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider">
            Local Brief
          </h3>
          <div className="flex gap-2">
            <button
              onClick={() => handleBrief(false)}
              disabled={briefMutation.isPending}
              className="text-xs px-2 py-1 rounded bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#30363d] disabled:opacity-50"
            >
              {briefMutation.isPending ? 'Generating...' : localBrief ? 'Refresh' : 'Generate'}
            </button>
          </div>
        </div>
        {localBrief ? (
          <>
            <p className="text-sm leading-relaxed">{localBrief.summary}</p>
            <div className="text-xs text-[#8b949e] mt-2">
              Model: {localBrief.model} | {new Date(localBrief.generated_at).toLocaleTimeString()}
            </div>
          </>
        ) : briefMutation.isPending ? (
          <div className="text-[#8b949e] text-sm animate-pulse">Generating local brief...</div>
        ) : (
          <div className="text-[#8b949e] text-sm">Click Generate to create a local brief.</div>
        )}
        {briefMutation.isError && (
          <div className="text-[#f85149] text-sm mt-2">Error: {briefMutation.error.message}</div>
        )}
      </div>

      {/* Local News */}
      <div>
        <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider mb-3">
          Local News {newsLoading ? '' : `(${news?.length || 0})`}
        </h3>
        {newsLoading && <div className="text-[#8b949e] text-sm animate-pulse">Loading...</div>}
        <div className="space-y-1">
          {news?.map((item, i) => (
            <a
              key={i}
              href={item.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 rounded-lg border border-[#21262d] bg-[#161b22] hover:border-[#30363d] hover:bg-[#1c2128] transition-colors"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[#8b949e] text-xs">{item.source}</span>
                <span className="text-[#8b949e] text-xs ml-auto">{timeAgo(item.published)}</span>
              </div>
              <div className="text-sm">{item.title}</div>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
