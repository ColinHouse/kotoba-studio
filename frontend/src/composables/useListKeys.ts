import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'

/** True when the event target is a field where letters are text, not commands. */
export function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null
  if (!el || typeof el.tagName !== 'string') return false
  return (
    el.tagName === 'INPUT' ||
    el.tagName === 'TEXTAREA' ||
    el.tagName === 'SELECT' ||
    el.isContentEditable === true
  )
}

export interface ListKeyOptions {
  onEnter?: (index: number) => void
  onHelp?: () => void
}

/**
 * List navigation for the mining path: j/k or the arrows move a cursor, Enter
 * acts on it, `?` explains. Two things must never happen while the reader is
 * working: a single letter firing inside a text field (typing a reading is not
 * a command), and us swallowing a browser shortcut (⌘F, Ctrl+R) — hence the
 * modifier guard, which returns before preventDefault.
 */
export function useListKeys(count: Ref<number>, options: ListKeyOptions = {}) {
  const cursor = ref(0)

  watch(count, (now) => {
    if (cursor.value > now - 1) cursor.value = Math.max(0, now - 1)
  })

  function move(step: number) {
    const total = count.value
    if (!total) return
    cursor.value = Math.min(total - 1, Math.max(0, cursor.value + step))
  }

  function onKey(event: KeyboardEvent) {
    if (event.metaKey || event.ctrlKey || event.altKey) return
    if (isTypingTarget(event.target)) return
    switch (event.key) {
      case 'j':
      case 'ArrowDown':
        move(1)
        event.preventDefault()
        break
      case 'k':
      case 'ArrowUp':
        move(-1)
        event.preventDefault()
        break
      case 'Enter':
        if (count.value) options.onEnter?.(cursor.value)
        break
      case '?':
        options.onHelp?.()
        event.preventDefault()
        break
    }
  }

  onMounted(() => window.addEventListener('keydown', onKey))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

  return { cursor, move, onKey }
}
