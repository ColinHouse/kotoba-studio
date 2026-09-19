/** 采集域接口：OCR 引擎对比、默认引擎设置、Hook 文本源。 */
import { api } from './client'
import type { CompareResult, HookProbe, HookStatus, Region, Settings } from './types'

export function compareOcr(region: Region): Promise<CompareResult[]> {
  return api.post<CompareResult[]>('/api/capture/ocr/compare', { region })
}

export function setOcrProvider(provider: string): Promise<Settings> {
  return api.put<Settings>('/api/settings', { ocr_provider: provider })
}

export function listHooks(): Promise<HookStatus[]> {
  return api.get<HookStatus[]>('/api/capture/hooks')
}

export function connectHook(name: string, url?: string): Promise<HookStatus> {
  return api.post<HookStatus>(`/api/capture/hooks/${name}/connect`, { url: url ?? null })
}

export function disconnectHook(name: string): Promise<HookStatus> {
  return api.post<HookStatus>(`/api/capture/hooks/${name}/disconnect`)
}

export function probeHook(name: string, url?: string): Promise<HookProbe> {
  return api.post<HookProbe>(`/api/capture/hooks/${name}/probe`, { url: url ?? null })
}
