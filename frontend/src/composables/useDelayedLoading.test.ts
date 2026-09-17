import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, ref } from 'vue'
import { useDelayedLoading } from './useDelayedLoading'

describe('useDelayedLoading', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not show skeleton if loading finishes before threshold', () => {
    const scope = effectScope()
    scope.run(() => {
      const loading = ref(true)
      const showLoading = useDelayedLoading(loading, 200)

      expect(showLoading.value).toBe(false)

      // Fast response after 100ms
      vi.advanceTimersByTime(100)
      loading.value = false
      expect(showLoading.value).toBe(false)

      // Reach 200ms, still false
      vi.advanceTimersByTime(150)
      expect(showLoading.value).toBe(false)
    })
    scope.stop()
  })

  it('shows skeleton after threshold when loading persists', () => {
    const scope = effectScope()
    scope.run(() => {
      const loading = ref(true)
      const showLoading = useDelayedLoading(loading, 200)

      expect(showLoading.value).toBe(false)

      // At 199ms, still false
      vi.advanceTimersByTime(199)
      expect(showLoading.value).toBe(false)

      // At 200ms, turns true
      vi.advanceTimersByTime(1)
      expect(showLoading.value).toBe(true)

      // When loading finally ends
      loading.value = false
      expect(showLoading.value).toBe(false)
    })
    scope.stop()
  })
})
