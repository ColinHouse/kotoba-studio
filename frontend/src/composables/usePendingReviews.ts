import { onScopeDispose, ref } from 'vue'
import { ApiError, api } from '@/api/client'
import type { CardFace } from '@/api/types'

/**
 * Reviews recorded while the phone is offline, kept in localStorage until the
 * server accepts them (ADR 0004). Each entry carries a client-generated id so a
 * retry after a lost response cannot count the same review twice.
 */

const PENDING_KEY = 'kotoba.pending_reviews'
const QUEUE_KEY = 'kotoba.offline_queue'

export interface PendingReview {
  client_id: string
  card_id: number
  rating: 1 | 2 | 3 | 4
  reviewed_at: string
  device_id: string | null
  duration_ms: number | null
}

export interface SyncResult {
  applied: number
  skipped: number
  failed: { client_id: string; reason: string }[]
}

function read<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null // private mode or corrupt value: behave as if empty
  }
}

function write(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* private mode: keep the in-memory copy */
  }
}

export function newReviewId(): string {
  try {
    return crypto.randomUUID()
  } catch {
    return `r-${Date.now()}-${Math.random().toString(16).slice(2)}`
  }
}

/** The last queue the server handed out, so a phone that loses signal can still review. */
export function loadCachedQueue(): CardFace[] {
  return read<CardFace[]>(QUEUE_KEY) ?? []
}

export function cacheQueue(cards: CardFace[]): void {
  write(QUEUE_KEY, cards)
}

export function usePendingReviews() {
  const pending = ref<PendingReview[]>(read<PendingReview[]>(PENDING_KEY) ?? [])
  const syncing = ref(false)

  function enqueue(entry: PendingReview): void {
    pending.value.push(entry)
    write(PENDING_KEY, pending.value)
  }

  async function flush(): Promise<SyncResult | null> {
    if (!pending.value.length || syncing.value) return null
    const batch = [...pending.value]
    syncing.value = true
    try {
      const result = await api.post<SyncResult>('/api/reviews/sync', { reviews: batch })
      const rejected = new Set(result.failed.map((f) => f.client_id))
      pending.value = pending.value.filter((entry) => rejected.has(entry.client_id))
      write(PENDING_KEY, pending.value)
      return result
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) return null // still offline; keep everything
      throw e
    } finally {
      syncing.value = false
    }
  }

  const onOnline = () => {
    void flush().catch(() => {})
  }
  if (typeof window !== 'undefined') {
    window.addEventListener('online', onOnline)
    onScopeDispose(() => window.removeEventListener('online', onOnline))
  }

  return { pending, syncing, enqueue, flush }
}
