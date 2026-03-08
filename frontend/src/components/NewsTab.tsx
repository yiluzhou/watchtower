import { useGlobalNews, useBrief } from '../hooks/useApi'
import { THREAT_LABELS, THREAT_COLORS } from '../types'
import type { ThreatLevel, Brief } from '../types'
import { useState } from 'react'

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

export default function NewsTab({ refetchInterval }: Props) {
  const { data: news, isLoading } = useGlobalNews(refetchInterval)
  const briefMutation = useBrief()
  const [brief, setBrief] = useState<Brief | null>(null)

  const handleGenerateBrief = () => {
    briefMutation.mutate({ force_refresh: false }, { onSuccess: (data) => setBrief(data) })
  }

  if (isLoading) {
    return (
      <div className="p-4 text-[#8b949e] animate-pulse">Loading global news...</div>
    )
  }

  const countryRisks = brief?.country_risks || []

  return (
    <div className="flex flex-col lg:flex-row gap-4 p-4">
      {/* Sidebar: Country Risk Index */}
      <div className="lg:w-72 shrink-0">
        <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4 sticky top-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider">
              Country Risk Index
            </h3>
            {!brief && (
              <button
                onClick={handleGenerateBrief}
                disabled={briefMutation.isPending}
                className="text-xs px-2 py-1 rounded bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#30363d] disabled:opacity-50"
              >
                {briefMutation.isPending ? '...' : 'Load'}
              </button>
            )}
          </div>
          {countryRisks.length === 0 && (
            <div className="text-[#8b949e] text-xs">
              {briefMutation.isPending ? 'Generating...' : 'Click Load to generate risk scores'}
            </div>
          )}
          <div className="space-y-2">
            {countryRisks.map((cr) => (
              <div key={cr.country}>
                <div className="flex justify-between text-xs mb-1">
                  <span>{cr.country}</span>
                  <span className={cr.score >= 70 ? 'text-[#f85149]' : cr.score >= 40 ? 'text-[#d29922]' : 'text-[#3fb950]'}>
                    {cr.score}
                  </span>
                </div>
                <div className="w-full bg-[#21262d] rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all ${
                      cr.score >= 70 ? 'bg-[#f85149]' : cr.score >= 40 ? 'bg-[#d29922]' : 'bg-[#3fb950]'
                    }`}
                    style={{ width: `${cr.score}%` }}
                  />
                </div>
                <div className="text-[10px] text-[#8b949e]">{cr.reason}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main: News Feed */}
      <div className="flex-1 space-y-1">
        <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider mb-3">
          Global News ({news?.length || 0} articles)
        </h3>
        {news?.map((item, i) => (
          <a
            key={i}
            href={item.url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-3 rounded-lg border border-[#21262d] bg-[#161b22] hover:border-[#30363d] hover:bg-[#1c2128] transition-colors"
          >
            <div className="flex items-center gap-2 mb-1">
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${THREAT_COLORS[item.threat_level as ThreatLevel]} text-white`}>
                {THREAT_LABELS[item.threat_level as ThreatLevel]}
              </span>
              <span className="text-[#8b949e] text-xs">{item.source}</span>
              <span className="text-[#8b949e] text-xs ml-auto">{timeAgo(item.published)}</span>
            </div>
            <div className="text-sm">{item.title}</div>
          </a>
        ))}
      </div>
    </div>
  )
}
