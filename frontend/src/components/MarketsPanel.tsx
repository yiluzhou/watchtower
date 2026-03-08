import type { MarketsResponse } from '../types'

function formatPrice(p: number): string {
  if (p >= 1000) return '$' + p.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  if (p >= 1) return '$' + p.toFixed(2)
  if (p >= 0.01) return '$' + p.toFixed(4)
  return '$' + p.toFixed(6)
}

function formatLargeNum(n: number): string {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
  if (n >= 1e9) return `$${(n / 1e9).toFixed(2)}B`
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)}M`
  return `$${n.toFixed(0)}`
}

function ChangeIndicator({ value }: { value: number }) {
  const color = value >= 0 ? 'text-[#3fb950]' : 'text-[#f85149]'
  const arrow = value >= 0 ? '↑' : '↓'
  return <span className={color}>{arrow} {Math.abs(value).toFixed(2)}%</span>
}

interface Props {
  data: MarketsResponse | undefined
  isLoading: boolean
}

export default function MarketsPanel({ data, isLoading }: Props) {
  if (isLoading || !data) {
    return (
      <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4">
        <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider mb-3">Markets</h3>
        <div className="text-[#8b949e] text-sm animate-pulse">Loading markets...</div>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4 space-y-4">
      {/* Crypto */}
      {data.crypto.length > 0 && (
        <div>
          <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider mb-2">Crypto</h3>
          <div className="space-y-1">
            {data.crypto.map((c) => (
              <div key={c.id} className="flex justify-between items-center text-sm py-1 border-b border-[#21262d]">
                <div>
                  <span className="font-semibold">{c.symbol}</span>
                  <span className="text-[#8b949e] ml-2 text-xs">{c.name}</span>
                </div>
                <div className="text-right">
                  <span className="mr-3">{formatPrice(c.price_usd)}</span>
                  <ChangeIndicator value={c.change_24h} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Stocks */}
      {data.stocks.length > 0 && (
        <div>
          <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider mb-2">Indices</h3>
          <div className="space-y-1">
            {data.stocks.map((s) => (
              <div key={s.symbol} className="flex justify-between items-center text-sm py-1 border-b border-[#21262d]">
                <span className="font-semibold">{s.name}</span>
                <div className="text-right">
                  <span className="mr-3">{formatPrice(s.price)}</span>
                  <ChangeIndicator value={s.change_pct} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Commodities */}
      {data.commodities.length > 0 && (
        <div>
          <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider mb-2">Commodities</h3>
          <div className="space-y-1">
            {data.commodities.map((c) => (
              <div key={c.symbol} className="flex justify-between items-center text-sm py-1 border-b border-[#21262d]">
                <div>
                  <span className="font-semibold">{c.name}</span>
                  <span className="text-[#8b949e] ml-2 text-xs">{c.unit}</span>
                </div>
                <div className="text-right">
                  <span className="mr-3">{formatPrice(c.price)}</span>
                  <ChangeIndicator value={c.change_pct} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Polymarket */}
      {data.polymarket.length > 0 && (
        <div>
          <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider mb-2">Prediction Markets</h3>
          <div className="space-y-2">
            {data.polymarket.slice(0, 8).map((m) => (
              <div key={m.slug} className="bg-[#0d1117] rounded p-2 text-xs">
                <div className="mb-1">{m.title}</div>
                <div className="flex justify-between text-[#8b949e]">
                  <span className="text-[#58a6ff] font-semibold">{(m.probability * 100).toFixed(0)}% Yes</span>
                  <span>Vol: {formatLargeNum(m.volume)}</span>
                </div>
                <div className="w-full bg-[#21262d] rounded-full h-1.5 mt-1">
                  <div
                    className="bg-[#58a6ff] h-1.5 rounded-full transition-all"
                    style={{ width: `${m.probability * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
