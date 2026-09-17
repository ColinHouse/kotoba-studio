import { ref, watch } from 'vue'
import { api } from '@/api/client'
import type { Line, Session } from '@/api/types'
import { useAppStore } from '@/stores/app'

export type LineStatus = 'inbox' | 'kept' | 'discarded'
export type LineSort = 'recent' | 'iplus1'

/** The inbox list: which session and status are shown, and what is selected. */
export function useInboxLines() {
  const app = useAppStore()
  const sessions = ref<Session[]>([])
  const sessionId = ref<number | 'all'>('all')
  const status = ref<LineStatus>('inbox')
  const sort = ref<LineSort>('recent')
  const lines = ref<Line[]>([])
  const selected = ref<Line | null>(null)

  async function loadSessions(preferred?: string | null) {
    sessions.value = await api.get<Session[]>('/api/sessions?limit=30')
    if (preferred) sessionId.value = Number(preferred)
    else if (app.activeSession) sessionId.value = app.activeSession.id
  }

  async function loadLines() {
    const params = new URLSearchParams({ status: status.value, limit: '200' })
    if (sessionId.value !== 'all') params.set('session_id', String(sessionId.value))
    if (sort.value !== 'recent') params.set('sort', sort.value)
    lines.value = await api.get<Line[]>(`/api/lines?${params}`)
    if (selected.value && !lines.value.some((l) => l.id === selected.value!.id)) {
      selected.value = null
    }
  }

  async function setStatus(line: Line, next: LineStatus) {
    try {
      const updated = await api.patch<Line>(`/api/lines/${line.id}`, { status: next })
      Object.assign(line, updated)
      if (next !== status.value) {
        lines.value = lines.value.filter((l) => l.id !== line.id)
        if (selected.value?.id === line.id) selected.value = null
      }
    } catch (e) {
      app.fail(e)
    }
  }

  async function discardRest() {
    if (!window.confirm(`把剩余 ${lines.value.length} 句全部标记为丢弃？`)) return
    for (const line of [...lines.value]) await setStatus(line, 'discarded')
  }

  watch([sessionId, status, sort], () => loadLines().catch(app.fail))

  return {
    sessions,
    sessionId,
    status,
    sort,
    lines,
    selected,
    loadSessions,
    loadLines,
    setStatus,
    discardRest,
  }
}
