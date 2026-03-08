import { useEffect, useMemo, useState } from 'react'
import { useConfig, useLocalCapabilities, useUpdateConfig } from '../hooks/useApi'

const PROVIDERS = [
  { value: 'groq', label: 'Groq (Free)', hint: 'llama-3.1-8b-instant' },
  { value: 'openai', label: 'OpenAI', hint: 'gpt-4o-mini' },
  { value: 'chatgpt', label: 'ChatGPT Subscription', hint: 'Uses Codex OAuth' },
  { value: 'claude', label: 'Anthropic Claude', hint: 'claude-3-haiku' },
  { value: 'deepseek', label: 'DeepSeek', hint: 'deepseek-chat' },
  { value: 'gemini', label: 'Google Gemini', hint: 'gemini-1.5-flash' },
  { value: 'local', label: 'Local (Ollama)', hint: 'qwen3.5:9b, llama3, etc.' },
]

export default function Settings() {
  const { data: config, isLoading } = useConfig()
  const updateConfig = useUpdateConfig()

  const [provider, setProvider] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('')
  const [city, setCity] = useState('')
  const [country, setCountry] = useState('')
  const [tempUnit, setTempUnit] = useState('celsius')
  const [refreshSec, setRefreshSec] = useState(120)
  const [cryptoPairs, setCryptoPairs] = useState('')
  const [cacheMin, setCacheMin] = useState(60)
  const [saved, setSaved] = useState(false)
  const [modelSearch, setModelSearch] = useState('')
  const localCaps = useLocalCapabilities(provider === 'local')

  useEffect(() => {
    if (config) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setProvider(config.llm_provider)
      setModel(config.llm_model)
      setCity(config.city)
      setCountry(config.country)
      setTempUnit(config.temp_unit)
      setRefreshSec(config.refresh_seconds)
      setCryptoPairs(config.crypto_pairs.join(', '))
      setCacheMin(config.brief_cache_minutes)
    }
  }, [config])

  const filteredLocalModels = useMemo(() => {
    const models = localCaps.data?.models ?? []
    const q = modelSearch.trim().toLowerCase()
    if (!q) return models
    return models.filter((m) => {
      const haystack = [m.name, m.label, m.family, m.focus, ...m.keywords].join(' ').toLowerCase()
      return haystack.includes(q)
    })
  }, [localCaps.data?.models, modelSearch])

  const selectedLocalModel = useMemo(
    () => (localCaps.data?.models ?? []).find((m) => m.name === model) ?? null,
    [localCaps.data?.models, model],
  )

  const handleSave = () => {
    const pairs = cryptoPairs.split(',').map((s) => s.trim()).filter(Boolean)
    updateConfig.mutate(
      {
        llm_provider: provider,
        ...(apiKey ? { llm_api_key: apiKey } : {}),
        llm_model: model,
        city,
        country,
        temp_unit: tempUnit,
        refresh_seconds: refreshSec,
        crypto_pairs: pairs,
        brief_cache_minutes: cacheMin,
      },
      {
        onSuccess: () => {
          setSaved(true)
          setApiKey('')
          setTimeout(() => setSaved(false), 3000)
        },
      },
    )
  }

  if (isLoading) {
    return <div className="p-4 text-[#8b949e] animate-pulse">Loading settings...</div>
  }

  return (
    <div className="p-4 max-w-2xl mx-auto space-y-6">
      <h2 className="text-xl font-bold text-[#58a6ff]">Settings</h2>

      {/* LLM Provider */}
      <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4 space-y-4">
        <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider">AI Provider</h3>

        <div className="grid grid-cols-2 gap-2">
          {PROVIDERS.map((p) => (
            <button
              key={p.value}
              onClick={() => setProvider(p.value)}
              className={`p-3 rounded-lg border text-left text-sm transition-colors ${
                provider === p.value
                  ? 'border-[#58a6ff] bg-[#0d1117]'
                  : 'border-[#21262d] bg-[#0d1117] hover:border-[#30363d]'
              }`}
            >
              <div className="font-semibold">{p.label}</div>
              <div className="text-[#8b949e] text-xs">{p.hint}</div>
            </button>
          ))}
        </div>

        {provider !== 'local' && provider !== 'chatgpt' && (
          <div>
            <label className="text-sm text-[#8b949e] block mb-1">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={config?.llm_api_key_set ? '••••••••••• (already set)' : 'Enter API key'}
              className="w-full px-3 py-2 rounded bg-[#0d1117] border border-[#30363d] text-sm focus:border-[#58a6ff] focus:outline-none"
            />
          </div>
        )}

        {provider === 'chatgpt' && (
          <div className="text-xs text-[#8b949e] bg-[#0d1117] p-3 rounded">
            Uses OpenAI Codex OAuth to authenticate with your ChatGPT subscription.
            No separate API key needed — uses your monthly subscription quota.
          </div>
        )}

        {provider === 'local' && (
          <div className="text-xs text-[#8b949e] bg-[#0d1117] p-3 rounded space-y-3">
            <div className="font-semibold text-[#e6edf3]">Local Runtime Detection</div>

            {localCaps.isLoading && (
              <div className="animate-pulse">Detecting GPU and local model capabilities...</div>
            )}

            {localCaps.data && (
              <>
                <div>
                  GPU: <span className="text-[#e6edf3]">{localCaps.data.gpu.name}</span>
                  {' '}| Free VRAM:{' '}
                  <span className="text-[#58a6ff]">
                    {localCaps.data.gpu.free_vram_gb.toFixed(1)} / {localCaps.data.gpu.total_vram_gb.toFixed(1)} GB
                  </span>
                </div>
                <div>
                  Ollama: {' '}
                  <span className={localCaps.data.ollama.installed ? 'text-[#3fb950]' : 'text-[#f85149]'}>
                    {localCaps.data.ollama.installed ? 'installed' : 'not installed'}
                  </span>
                  {' '}| Service:{' '}
                  <span className={localCaps.data.ollama.running ? 'text-[#3fb950]' : 'text-[#8b949e]'}>
                    {localCaps.data.ollama.running ? 'running' : 'starting/offline'}
                  </span>
                </div>

                <div className="bg-[#0b1220] border border-[#30363d] rounded p-2 space-y-1">
                  <div>Best reasoning: <button className="text-[#58a6ff]" onClick={() => setModel(localCaps.data!.recommendations.best_reasoning)}>{localCaps.data.recommendations.best_reasoning || 'n/a'}</button></div>
                  <div>Best speed: <button className="text-[#58a6ff]" onClick={() => setModel(localCaps.data!.recommendations.best_speed)}>{localCaps.data.recommendations.best_speed || 'n/a'}</button></div>
                  <div>Best overall: <button className="text-[#58a6ff]" onClick={() => setModel(localCaps.data!.recommendations.best_overall)}>{localCaps.data.recommendations.best_overall || 'n/a'}</button></div>
                  <div className={localCaps.data.recommendations.qwen35_27b_can_run ? 'text-[#3fb950]' : 'text-[#d29922]'}>
                    Qwen 3.5 27B fit: {localCaps.data.recommendations.qwen35_27b_note}
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm text-[#8b949e] block">Search local models</label>
                  <input
                    value={modelSearch}
                    onChange={(e) => setModelSearch(e.target.value)}
                    placeholder="Type keywords: reasoning, fast, qwen, coding..."
                    className="w-full px-3 py-2 rounded bg-[#0d1117] border border-[#30363d] text-sm focus:border-[#58a6ff] focus:outline-none"
                  />

                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-[#0d1117] border border-[#30363d] text-sm focus:border-[#58a6ff] focus:outline-none"
                  >
                    <option value="">Select a model...</option>
                    {filteredLocalModels.map((m) => (
                      <option key={m.name} value={m.name}>
                        {m.label} | {m.est_vram_gb}GB | {m.focus} | {m.fit}{m.installed ? ' | installed' : ''}{!m.auto_pull ? ' | manual import' : ''}
                      </option>
                    ))}
                  </select>

                  {filteredLocalModels.length === 0 && (
                    <div className="text-[#f85149]">No models matched your keywords.</div>
                  )}

                  {selectedLocalModel?.install_hint && !selectedLocalModel.installed && (
                    <div className="rounded border border-[#30363d] bg-[#0b1220] p-3 text-[#d29922]">
                      {selectedLocalModel.install_hint}
                    </div>
                  )}
                </div>
              </>
            )}

            {localCaps.isError && (
              <div className="text-[#f85149]">Could not load local capabilities.</div>
            )}

            <div>
              Watchtower can auto-install/start Ollama and pull the selected model when needed.
              Manual fallback: <code className="text-[#58a6ff]">ollama pull qwen3.5:9b</code>
            </div>
          </div>
        )}

        <div>
          <label className="text-sm text-[#8b949e] block mb-1">Model Override (optional)</label>
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="Leave empty for default"
            className="w-full px-3 py-2 rounded bg-[#0d1117] border border-[#30363d] text-sm focus:border-[#58a6ff] focus:outline-none"
          />
        </div>
      </div>

      {/* Location */}
      <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4 space-y-4">
        <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider">Location</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-[#8b949e] block mb-1">City</label>
            <input
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="New York"
              className="w-full px-3 py-2 rounded bg-[#0d1117] border border-[#30363d] text-sm focus:border-[#58a6ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-sm text-[#8b949e] block mb-1">Country Code</label>
            <input
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              placeholder="US"
              maxLength={2}
              className="w-full px-3 py-2 rounded bg-[#0d1117] border border-[#30363d] text-sm focus:border-[#58a6ff] focus:outline-none uppercase"
            />
          </div>
        </div>
      </div>

      {/* Preferences */}
      <div className="rounded-lg border border-[#30363d] bg-[#161b22] p-4 space-y-4">
        <h3 className="text-[#d29922] font-semibold text-sm uppercase tracking-wider">Preferences</h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-[#8b949e] block mb-1">Temperature Unit</label>
            <select
              value={tempUnit}
              onChange={(e) => setTempUnit(e.target.value)}
              className="w-full px-3 py-2 rounded bg-[#0d1117] border border-[#30363d] text-sm focus:border-[#58a6ff] focus:outline-none"
            >
              <option value="celsius">Celsius</option>
              <option value="fahrenheit">Fahrenheit</option>
            </select>
          </div>
          <div>
            <label className="text-sm text-[#8b949e] block mb-1">Refresh Interval (sec)</label>
            <input
              type="number"
              value={refreshSec}
              onChange={(e) => setRefreshSec(Number(e.target.value))}
              min={30}
              className="w-full px-3 py-2 rounded bg-[#0d1117] border border-[#30363d] text-sm focus:border-[#58a6ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-sm text-[#8b949e] block mb-1">Brief Cache (minutes)</label>
            <input
              type="number"
              value={cacheMin}
              onChange={(e) => setCacheMin(Number(e.target.value))}
              min={1}
              className="w-full px-3 py-2 rounded bg-[#0d1117] border border-[#30363d] text-sm focus:border-[#58a6ff] focus:outline-none"
            />
          </div>
          <div>
            <label className="text-sm text-[#8b949e] block mb-1">Crypto Pairs</label>
            <input
              value={cryptoPairs}
              onChange={(e) => setCryptoPairs(e.target.value)}
              placeholder="bitcoin, ethereum"
              className="w-full px-3 py-2 rounded bg-[#0d1117] border border-[#30363d] text-sm focus:border-[#58a6ff] focus:outline-none"
            />
          </div>
        </div>
      </div>

      {/* Save */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={updateConfig.isPending}
          className="px-6 py-2 rounded-lg bg-[#58a6ff] text-black font-semibold text-sm hover:bg-[#79c0ff] disabled:opacity-50 transition-colors"
        >
          {updateConfig.isPending ? 'Saving...' : 'Save Settings'}
        </button>
        {saved && <span className="text-[#3fb950] text-sm">Settings saved!</span>}
        {updateConfig.isError && <span className="text-[#f85149] text-sm">Error: {updateConfig.error.message}</span>}
      </div>
    </div>
  )
}
