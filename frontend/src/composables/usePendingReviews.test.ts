import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { ApiError } from '@/api/client'
import { usePendingReviews, type PendingReview } from './usePendingReviews'

const { post } = vi.hoisted(() => ({ post: vi.fn() }))
vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>()
  return { ...actual, api: { ...actual.api, post } }
})

const ENTRY: PendingReview = {
  client_id: 'client-1234',
  card_id: 7,
  rating: 3,
  reviewed_at: '2026-09-17T09:00:00.000Z',
  device_id: 'device-1',
  duration_ms: 4200,
}

let store: Record<string, string>

beforeEach(() => {
  store = {}
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value
    },
  })
  post.mockReset()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function withQueue<T>(fn: () => T): T {
  const scope = effectScope()
  const result = scope.run(fn)!
  scope.stop()
  return result
}

describe('usePendingReviews', () => {
  it('persists queued reviews and keeps everything when still offline', async () => {
    post.mockRejectedValue(new ApiError('network', '无法连接服务器', 0))
    const sync = withQueue(() => usePendingReviews())
    sync.enqueue(ENTRY)
    expect(JSON.parse(store['kotoba.pending_reviews']!)).toEqual([ENTRY])

    expect(await sync.flush()).toBeNull()
    expect(sync.pending.value).toEqual([ENTRY])
  })

  it('clears accepted reviews and keeps only the rejected ones', async () => {
    post.mockResolvedValue({
      applied: 1,
      skipped: 0,
      failed: [{ client_id: 'client-gone', reason: 'not_found' }],
    })
    const sync = withQueue(() => usePendingReviews())
    sync.enqueue(ENTRY)
    sync.enqueue({ ...ENTRY, client_id: 'client-gone' })

    const result = await sync.flush()
    expect(post).toHaveBeenCalledWith('/api/reviews/sync', {
      reviews: [ENTRY, { ...ENTRY, client_id: 'client-gone' }],
    })
    expect(result?.applied).toBe(1)
    expect(sync.pending.value.map((e) => e.client_id)).toEqual(['client-gone'])
    expect(
      JSON.parse(store['kotoba.pending_reviews']!).map((e: PendingReview) => e.client_id),
    ).toEqual(['client-gone'])
  })

  it('reloads the queue from storage on the next visit', () => {
    store['kotoba.pending_reviews'] = JSON.stringify([ENTRY])
    const sync = withQueue(() => usePendingReviews())
    expect(sync.pending.value).toEqual([ENTRY])
  })
})
