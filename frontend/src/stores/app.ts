import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, ApiError } from '@/api/client'
import { translateError } from '@/i18n'
import type { Session, Settings } from '@/api/types'

export interface Toast {
  id: number
  text: string
  kind: 'info' | 'error' | 'success'
}

export const useAppStore = defineStore('app', () => {
  const health = ref<{ status: string; version: string; platform: string } | null>(null)
  const offline = ref(false)
  const settings = ref<Settings | null>(null)
  const activeSession = ref<Session | null>(null)
  const toasts = ref<Toast[]>([])
  let seq = 0

  const serverPlatform = computed(() => health.value?.platform ?? 'unknown')

  async function refreshHealth() {
    try {
      health.value = await api.get('/api/health')
      offline.value = false
    } catch {
      offline.value = true
    }
  }

  async function refreshSettings() {
    try {
      settings.value = await api.get<Settings>('/api/settings')
      activeSession.value = await api.get<Session | null>('/api/sessions/active')
    } catch {
      /* offline */
    }
  }

  function toast(text: string, kind: Toast['kind'] = 'info') {
    const id = ++seq
    toasts.value.push({ id, text, kind })
    setTimeout(
      () => {
        toasts.value = toasts.value.filter((t) => t.id !== id)
      },
      kind === 'error' ? 6000 : 3000,
    )
  }

  function fail(err: unknown, fallback = '操作失败') {
    // 中文下 translateError 原样返回后端 message；英文按 code 映射（#130 决策二）。
    const message = err instanceof ApiError ? translateError(err.code, err.message) : fallback
    toast(message, 'error')
  }

  return {
    health,
    offline,
    settings,
    activeSession,
    toasts,
    serverPlatform,
    refreshHealth,
    refreshSettings,
    toast,
    fail,
  }
})
