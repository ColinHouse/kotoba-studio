import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/client'
import type { Device } from '@/api/types'

const KEY = 'kotoba.device'

export function detectKind(): 'desktop' | 'mobile' {
  const coarse = window.matchMedia?.('(pointer: coarse)').matches
  const narrow = window.innerWidth < 900
  const ua = /iPhone|iPad|Android|Mobile/i.test(navigator.userAgent)
  return (coarse && narrow) || ua ? 'mobile' : 'desktop'
}

function defaultName(kind: 'desktop' | 'mobile'): string {
  const ua = navigator.userAgent
  if (/iPhone/.test(ua)) return 'iPhone'
  if (/iPad/.test(ua)) return 'iPad'
  if (/Android/.test(ua)) return 'Android'
  if (/Mac/.test(ua)) return 'Mac'
  if (/Windows/.test(ua)) return 'Windows PC'
  return kind === 'mobile' ? '手机' : '电脑'
}

export const useDeviceStore = defineStore('device', () => {
  const device = ref<Device | null>(null)
  const kind = ref<'desktop' | 'mobile'>(detectKind())
  const ready = ref(false)

  async function ensureRegistered() {
    let saved: { id: string; name: string; kind: 'desktop' | 'mobile' } | null = null
    try {
      saved = JSON.parse(localStorage.getItem(KEY) ?? 'null')
    } catch {
      saved = null
    }
    const body = saved ?? { name: defaultName(kind.value), kind: kind.value }
    try {
      device.value = await api.post<Device>('/api/devices/register', body)
      kind.value = device.value.kind
      try {
        localStorage.setItem(KEY, JSON.stringify({ id: device.value.id, name: device.value.name, kind: device.value.kind }))
      } catch {
        /* storage unavailable */
      }
    } finally {
      ready.value = true
    }
  }

  async function rename(name: string, newKind: 'desktop' | 'mobile') {
    device.value = await api.post<Device>('/api/devices/register', { id: device.value?.id, name, kind: newKind })
    kind.value = device.value.kind
    try {
      localStorage.setItem(KEY, JSON.stringify({ id: device.value.id, name, kind: newKind }))
    } catch {
      /* ignore */
    }
  }

  return { device, kind, ready, ensureRegistered, rename }
})
