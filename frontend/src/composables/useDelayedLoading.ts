import { onScopeDispose, ref, watch, type Ref } from 'vue'

/**
 * Delays the display of a loading skeleton by `delayMs` (default: 200ms).
 * If loading completes within 200ms, the skeleton never appears,
 * preventing distracting flashes on fast networks (criterion 6).
 */
export function useDelayedLoading(loading: Ref<boolean>, delayMs: number = 200): Ref<boolean> {
  const showLoading = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  const stop = watch(
    loading,
    (isLoading) => {
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
      if (isLoading) {
        timer = setTimeout(() => {
          if (loading.value) {
            showLoading.value = true
          }
        }, delayMs)
      } else {
        showLoading.value = false
      }
    },
    { immediate: true, flush: 'sync' },
  )

  onScopeDispose(() => {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    stop()
  })

  return showLoading
}
