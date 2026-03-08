import { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './components/Dashboard'
import NewsTab from './components/NewsTab'
import LocalTab from './components/LocalTab'
import Settings from './components/Settings'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

const TABS = [
  { key: 'overview', label: 'Overview', shortcut: '1' },
  { key: 'news', label: 'Global News', shortcut: '2' },
  { key: 'local', label: 'Local', shortcut: '3' },
  { key: 'settings', label: 'Settings', shortcut: '4' },
]

function AppContent() {
  const [activeTab, setActiveTab] = useState('overview')
  const refetchInterval = 120_000

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return
      switch (e.key) {
        case '1': setActiveTab('overview'); break
        case '2': setActiveTab('news'); break
        case '3': setActiveTab('local'); break
        case '4': setActiveTab('settings'); break
        case 'r':
          queryClient.invalidateQueries()
          break
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="min-h-screen bg-[#0d1117]">
      {/* Header */}
      <header className="border-b border-[#30363d] bg-[#161b22]">
        <div className="max-w-[1400px] mx-auto px-4 py-3 flex items-center justify-between">
          <h1 className="text-[#58a6ff] font-bold text-lg tracking-wide">
            WATCHTOWER
          </h1>
          <nav className="flex gap-1">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'bg-[#21262d] text-[#58a6ff]'
                    : 'text-[#8b949e] hover:text-[#e6edf3] hover:bg-[#21262d]'
                }`}
              >
                <span className="text-[#8b949e] text-xs mr-1">{tab.shortcut}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-[1400px] mx-auto">
        {activeTab === 'overview' && <Dashboard refetchInterval={refetchInterval} />}
        {activeTab === 'news' && <NewsTab refetchInterval={refetchInterval} />}
        {activeTab === 'local' && <LocalTab refetchInterval={refetchInterval} />}
        {activeTab === 'settings' && <Settings />}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  )
}
