import { onBeforeUnmount, ref, type Ref } from 'vue'
import { api, wsUrl } from '@/api/client'
import type { Line } from '@/api/types'

/** The lines of one capture session, kept live by the server's event stream. */
export function useSessionLines(sessionId: Ref<number | null>) {
  const lines = ref<Line[]>([])
  let socket: WebSocket | null = null

  function upsert(line: Line) {
    const index = lines.value.findIndex((l) => l.id === line.id)
    if (index >= 0) lines.value[index] = line
    else lines.value.unshift(line)
  }

  async function load() {
    if (sessionId.value == null) {
      lines.value = []
      return
    }
    lines.value = await api.get<Line[]>(`/api/lines?session_id=${sessionId.value}&limit=100`)
  }

  function connect() {
    try {
      socket = new WebSocket(wsUrl('/ws/events'))
      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data) as { type: string; line: Line }
        if (sessionId.value == null || payload.line.session_id !== sessionId.value) return
        upsert(payload.line)
      }
    } catch {
      socket = null
    }
  }

  function disconnect() {
    socket?.close()
    socket = null
  }

  onBeforeUnmount(disconnect)

  return { lines, upsert, load, connect, disconnect }
}
