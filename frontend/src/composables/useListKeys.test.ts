import { describe, expect, it, vi } from 'vitest'
import { effectScope, ref } from 'vue'
import { isTypingTarget, useListKeys } from './useListKeys'

function key(key: string, options: Partial<KeyboardEvent> = {}): KeyboardEvent {
  return {
    key,
    target: { tagName: 'BODY' },
    metaKey: false,
    ctrlKey: false,
    altKey: false,
    preventDefault: vi.fn(),
    ...options,
  } as unknown as KeyboardEvent
}

function withKeys<T>(
  count: number,
  options = {},
  run: (api: ReturnType<typeof useListKeys>) => T,
): T {
  const scope = effectScope()
  const total = ref(count)
  const api = scope.run(() => useListKeys(total, options))!
  const result = run(api)
  scope.stop()
  return result
}

describe('useListKeys', () => {
  it('moves the cursor with j/k and the arrows, and clamps at both ends', () => {
    withKeys(3, {}, ({ cursor, onKey }) => {
      onKey(key('j'))
      expect(cursor.value).toBe(1)
      onKey(key('ArrowDown'))
      expect(cursor.value).toBe(2)
      onKey(key('j'))
      expect(cursor.value).toBe(2)
      onKey(key('k'))
      onKey(key('ArrowUp'))
      onKey(key('k'))
      expect(cursor.value).toBe(0)
    })
  })

  it('does not move while a field has focus', () => {
    withKeys(3, {}, ({ cursor, onKey }) => {
      for (const tagName of ['INPUT', 'TEXTAREA', 'SELECT']) {
        onKey(key('j', { target: { tagName } }))
      }
      onKey(key('j', { target: { tagName: 'DIV', isContentEditable: true } }))
      expect(cursor.value).toBe(0)
    })
  })

  it('leaves browser shortcuts alone', () => {
    withKeys(3, {}, ({ cursor, onKey }) => {
      const event = key('j', { metaKey: true })
      onKey(event)
      expect(cursor.value).toBe(0)
      expect(event.preventDefault).not.toHaveBeenCalled()
    })
  })

  it('acts on the cursor on Enter and explains on ?', () => {
    const onEnter = vi.fn()
    const onHelp = vi.fn()
    withKeys(2, { onEnter, onHelp }, ({ onKey }) => {
      onKey(key('j'))
      onKey(key('Enter'))
      expect(onEnter).toHaveBeenCalledWith(1)
      onKey(key('?'))
      expect(onHelp).toHaveBeenCalledOnce()
    })
  })

  it('does not act on Enter in an empty list', () => {
    const onEnter = vi.fn()
    withKeys(0, { onEnter }, ({ onKey }) => {
      onKey(key('Enter'))
      expect(onEnter).not.toHaveBeenCalled()
    })
  })

  it('keeps the cursor inside a list that shrinks under it', async () => {
    const scope = effectScope()
    await scope.run(async () => {
      const total = ref(3)
      const { cursor } = useListKeys(total)
      cursor.value = 2
      total.value = 1
      await Promise.resolve()
      expect(cursor.value).toBe(0)
    })
    scope.stop()
  })

  it('recognises typing targets', () => {
    expect(isTypingTarget({ tagName: 'INPUT' } as unknown as EventTarget)).toBe(true)
    expect(isTypingTarget({ tagName: 'BODY' } as unknown as EventTarget)).toBe(false)
    expect(isTypingTarget(null)).toBe(false)
  })
})
