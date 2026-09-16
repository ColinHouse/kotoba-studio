import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { Settings } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { useOcrCompare } from './useOcrCompare'

const { compareOcr, setOcrProvider } = vi.hoisted(() => ({
  compareOcr: vi.fn(),
  setOcrProvider: vi.fn(),
}))

vi.mock('@/api/capture', () => ({ compareOcr, setOcrProvider }))

const REGION = { left: 10, top: 20, width: 300, height: 80, display: 0 }

const SETTINGS: Settings = {
  review_owner_default: null,
  desired_retention: 0.9,
  ai_provider: 'deepseek',
  ai_base_url: 'https://api.deepseek.com',
  ai_model: 'deepseek-flash',
  ocr_provider: 'vision',
  active_session_id: null,
  ui_language: 'zh-CN',
}

describe('useOcrCompare', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('runs every engine on the framed region', async () => {
    compareOcr.mockResolvedValueOnce([
      { provider: 'vision', text: 'おはよう', ms: 950, error: null },
      { provider: 'rapidocr', text: '', ms: 120, error: '模型未安装' },
    ])

    const compare = useOcrCompare()
    await compare.run(REGION)

    expect(compareOcr).toHaveBeenCalledWith(REGION)
    expect(compare.results.value.map((row) => row.provider)).toEqual(['vision', 'rapidocr'])
    expect(compare.running.value).toBe(false)
  })

  it('writes the chosen engine into settings', async () => {
    setOcrProvider.mockResolvedValueOnce(SETTINGS)
    const app = useAppStore()
    const compare = useOcrCompare()

    await compare.setDefault('vision')

    expect(setOcrProvider).toHaveBeenCalledWith('vision')
    expect(app.settings?.ocr_provider).toBe('vision')
    expect(app.toasts.some((toast) => toast.kind === 'success')).toBe(true)
  })

  it('stops the spinner and reports failures', async () => {
    compareOcr.mockRejectedValueOnce(new Error('offline'))
    const app = useAppStore()
    const compare = useOcrCompare()

    await compare.run(REGION)

    expect(compare.running.value).toBe(false)
    expect(app.toasts.some((toast) => toast.kind === 'error')).toBe(true)
  })
})
