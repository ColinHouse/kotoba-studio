/** 采集域接口：OCR 引擎对比与默认引擎设置。 */
import { api } from './client'
import type { CompareResult, Region, Settings } from './types'

export function compareOcr(region: Region): Promise<CompareResult[]> {
  return api.post<CompareResult[]>('/api/capture/ocr/compare', { region })
}

export function setOcrProvider(provider: string): Promise<Settings> {
  return api.put<Settings>('/api/settings', { ocr_provider: provider })
}
