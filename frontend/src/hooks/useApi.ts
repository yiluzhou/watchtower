import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  NewsItem, MarketsResponse, WeatherResponse, Brief, LocalBrief, ConfigResponse, LocalCapabilitiesResponse,
} from '../types'

const API_BASE = '/api'

async function fetchJson<T>(path: string): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`)
  if (!resp.ok) throw new Error(`API error: ${resp.status}`)
  return resp.json()
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : '{}',
  })
  if (!resp.ok) throw new Error(`API error: ${resp.status}`)
  return resp.json()
}

export function useGlobalNews(refetchInterval: number) {
  return useQuery<NewsItem[]>({
    queryKey: ['globalNews'],
    queryFn: () => fetchJson('/news/global'),
    refetchInterval,
    staleTime: 30_000,
  })
}

export function useLocalNews(refetchInterval: number) {
  return useQuery<NewsItem[]>({
    queryKey: ['localNews'],
    queryFn: () => fetchJson('/news/local'),
    refetchInterval,
    staleTime: 30_000,
  })
}

export function useMarkets(refetchInterval: number) {
  return useQuery<MarketsResponse>({
    queryKey: ['markets'],
    queryFn: () => fetchJson('/markets'),
    refetchInterval,
    staleTime: 30_000,
  })
}

export function useWeather(refetchInterval: number) {
  return useQuery<WeatherResponse>({
    queryKey: ['weather'],
    queryFn: () => fetchJson('/weather'),
    refetchInterval,
    staleTime: 60_000,
  })
}

export function useBrief() {
  return useMutation<Brief, Error, { force_refresh?: boolean }>({
    mutationFn: (body) => postJson('/intel/brief', body),
  })
}

export function useLocalBrief() {
  return useMutation<LocalBrief, Error, { force_refresh?: boolean }>({
    mutationFn: (body) => postJson('/intel/local-brief', body),
  })
}

export function useLocalCapabilities(enabled = true) {
  return useQuery<LocalCapabilitiesResponse>({
    queryKey: ['localCapabilities'],
    queryFn: () => fetchJson('/intel/local-capabilities'),
    enabled,
    staleTime: 30_000,
    refetchInterval: enabled ? 60_000 : false,
  })
}

export function useConfig() {
  return useQuery<ConfigResponse>({
    queryKey: ['config'],
    queryFn: () => fetchJson('/config'),
    staleTime: Infinity,
  })
}

export function useUpdateConfig() {
  const queryClient = useQueryClient()
  return useMutation<ConfigResponse, Error, Record<string, unknown>>({
    mutationFn: (body) => postJson('/config', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] })
    },
  })
}
