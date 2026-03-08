import { useEffect } from 'react'
import { useBrief } from '../hooks/useApi'
import type { Brief } from '../types'

interface Props {
  brief: Brief | null
  onBriefLoaded: (b: Brief) => void
}

export default function BriefPanel({ brief, onBriefLoaded }: Props) {
  const mutation = useBrief()

  useEffect(() => {
    if (!brief && !mutation.isPending) {
      mutation.mutate({ force_refresh: false }, {
        onSuccess: (data) => onBriefLoaded(data),
      })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const b = brief || mutation.data

  return (
    <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider">
          Intel Brief
        </h3>
        <button
          onClick={() => mutation.mutate({ force_refresh: true }, { onSuccess: (data) => onBriefLoaded(data) })}
          disabled={mutation.isPending}
          className="text-xs px-2 py-1 rounded bg-[#21262d] text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#30363d] disabled:opacity-50 transition-colors"
        >
          {mutation.isPending ? 'Generating...' : 'Refresh'}
        </button>
      </div>

      {mutation.isPending && !b && (
        <div className="text-[#8b949e] text-sm animate-pulse">Generating AI brief...</div>
      )}

      {b && (
        <>
          <p className="text-sm leading-relaxed mb-3">{b.summary}</p>
          {b.key_threats.length > 0 && (
            <div className="mt-2">
              <div className="text-xs text-[#d29922] mb-1 font-semibold">Key Threats</div>
              <ul className="text-xs text-[#8b949e] space-y-1">
                {b.key_threats.map((t, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="text-[#f85149]">•</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {b.model !== 'none' && (
            <div className="text-xs text-[#8b949e] mt-3">
              Model: {b.model} | {new Date(b.generated_at).toLocaleTimeString()}
            </div>
          )}
        </>
      )}

      {mutation.isError && (
        <div className="text-sm text-[#f85149]">Error: {mutation.error.message}</div>
      )}
    </div>
  )
}
