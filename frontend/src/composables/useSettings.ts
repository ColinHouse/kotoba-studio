import { ref } from 'vue'
import { api } from '@/api/client'
import type { Settings } from '@/api/types'
import { useAppStore } from '@/stores/app'

/** Shared across every settings section so they read one copy and write through one path. */
const settings = ref<Settings | null>(null)
let inFlight: Promise<void> | null = null

export function useSettings() {
  const app = useAppStore()

  async function load(force = false): Promise<void> {
    if (settings.value && !force) return
    if (!inFlight || force) {
      inFlight = api
        .get<Settings>('/api/settings')
        .then((s) => {
          settings.value = s
          app.settings = s
        })
        .finally(() => {
          inFlight = null
        })
    }
    return inFlight
  }

  async function save(patch: Partial<Settings>): Promise<void> {
    try {
      const next = await api.put<Settings>('/api/settings', patch)
      settings.value = next
      app.settings = next
      app.toast('已保存', 'success')
    } catch (e) {
      app.fail(e)
    }
  }

  return { settings, load, save }
}
