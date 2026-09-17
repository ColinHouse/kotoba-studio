import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { Analysis, Line } from '@/api/types'
import type { ConfirmPayload } from '@/components/inbox/TermEditor.vue'
import { useAppStore } from '@/stores/app'
import { useTermBuilder } from './useTermBuilder'

const { post } = vi.hoisted(() => ({ post: vi.fn() }))

vi.mock('@/api/client', () => ({
  api: { post },
  ApiError: class ApiError extends Error {},
}))

const ANALYSIS: Analysis = { line_id: 7, text: '猫だ', tokens: [], spans: [], contractions: [] }

function line(): Line {
  return {
    id: 7,
    session_id: 1,
    source_id: 1,
    text: '猫だ',
    raw_text: null,
    origin: 'ocr',
    screenshot_path: null,
    audio_path: null,
    position: null,
    locator: null,
    ord: 1,
    speaker: null,
    translation_zh: null,
    status: 'inbox',
    captured_at: '2026-09-17T00:00:00Z',
    encounter_count: 0,
    unknown_count: null,
  }
}

const PAYLOAD: ConfirmPayload = {
  headword: '猫',
  reading: 'ねこ',
  surface: '猫',
  span_start: 0,
  span_end: 1,
  pos: null,
  jmdict_id: null,
  sense: null,
  card_types: ['meaning'],
}

describe('useTermBuilder', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('records the encounter, marks the line kept and refreshes the analysis', async () => {
    post.mockResolvedValueOnce({ term: { headword: '猫' }, encounter: { id: 3 } })
    post.mockResolvedValueOnce(ANALYSIS)
    const target = line()
    const builder = useTermBuilder()

    const ok = await builder.confirm(target, PAYLOAD)

    expect(ok).toBe(true)
    expect(post).toHaveBeenNthCalledWith(
      1,
      '/api/encounters',
      expect.objectContaining({ line_id: 7, headword: '猫' }),
    )
    expect(post).toHaveBeenNthCalledWith(2, '/api/lines/7/analyze')
    expect(target.status).toBe('kept')
    expect(target.encounter_count).toBe(1)
    expect(builder.analysis.value).toEqual(ANALYSIS)
    expect(builder.picked.value).toBeNull()
    expect(useAppStore().toasts.some((toast) => toast.kind === 'success')).toBe(true)
  })

  it('reports the failure and leaves the line alone', async () => {
    post.mockRejectedValueOnce(new Error('offline'))
    const target = line()
    const builder = useTermBuilder()

    const ok = await builder.confirm(target, PAYLOAD)

    expect(ok).toBe(false)
    expect(target.status).toBe('inbox')
    expect(target.encounter_count).toBe(0)
    expect(useAppStore().toasts.some((toast) => toast.kind === 'error')).toBe(true)
  })

  it('reports a failed analysis', async () => {
    post.mockRejectedValueOnce(new Error('offline'))
    const builder = useTermBuilder()

    await builder.analyze(line())

    expect(builder.analysis.value).toBeNull()
    expect(useAppStore().toasts.some((toast) => toast.kind === 'error')).toBe(true)
  })

  it('attaches the AI explanation to the recorded encounter', async () => {
    post.mockResolvedValueOnce({ term: { headword: '猫' }, encounter: { id: 3 } })
    post.mockResolvedValueOnce(ANALYSIS)
    const builder = useTermBuilder()
    await builder.confirm(line(), PAYLOAD)

    post.mockResolvedValueOnce({ explanation: { meaning_here: '这里是猫' } })
    await builder.explain()

    expect(post).toHaveBeenLastCalledWith('/api/ai/explain', { encounter_id: 3 })
    expect(builder.result.value?.encounter.ai_explanation).toEqual({ meaning_here: '这里是猫' })
  })
})
