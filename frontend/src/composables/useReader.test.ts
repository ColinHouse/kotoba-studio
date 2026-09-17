import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import type { ReaderPages } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { useReader } from './useReader'

const { get } = vi.hoisted(() => ({ get: vi.fn() }))

vi.mock('@/api/client', () => ({
  api: { get },
  ApiError: class ApiError extends Error {},
}))

function pages(): ReaderPages {
  return {
    source_id: 4,
    title: '漫画作品',
    title_ja: null,
    pages: [
      { page: 1, image: null, blocks: [] },
      { page: 2, image: null, blocks: [] },
    ],
  }
}

describe('useReader', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads the source pages', async () => {
    get.mockResolvedValueOnce(pages())
    const reader = useReader(4)

    await reader.load()

    expect(get).toHaveBeenCalledWith('/api/sources/4/pages')
    expect(reader.title.value).toBe('漫画作品')
    expect(reader.current.value?.page).toBe(1)
    expect(reader.loading.value).toBe(false)
  })

  it('clamps turning at both ends', async () => {
    get.mockResolvedValueOnce(pages())
    const reader = useReader(4)
    await reader.load()

    reader.turn('prev')
    expect(reader.index.value).toBe(0)
    reader.turn('next')
    reader.turn('next')
    expect(reader.index.value).toBe(1)
    reader.turn(null)
    expect(reader.index.value).toBe(1)
  })

  it('defaults to right-to-left', () => {
    expect(useReader(4).rtl.value).toBe(true)
  })

  it('reports a failed load', async () => {
    get.mockRejectedValueOnce(new Error('offline'))
    const reader = useReader(4)

    await reader.load()

    expect(reader.loading.value).toBe(false)
    expect(useAppStore().toasts.some((toast) => toast.kind === 'error')).toBe(true)
  })
})
