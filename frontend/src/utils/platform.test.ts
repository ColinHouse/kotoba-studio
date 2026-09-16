import { describe, expect, it } from 'vitest'
import { commandKey, confirmShortcut, isMac } from './platform'

const MAC = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15'
const IPAD = 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15'
const WINDOWS = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0'

describe('platform shortcut labels', () => {
  it('uses the command key on Apple platforms', () => {
    expect(commandKey(MAC)).toBe('⌘')
    expect(commandKey(IPAD)).toBe('⌘')
    expect(confirmShortcut(MAC)).toBe('⌘↵')
  })

  it('uses Ctrl on Windows and other platforms', () => {
    expect(isMac(WINDOWS)).toBe(false)
    expect(commandKey(WINDOWS)).toBe('Ctrl')
    expect(confirmShortcut(WINDOWS)).toBe('Ctrl+↵')
    expect(confirmShortcut('Mozilla/5.0 (X11; Linux x86_64)')).toBe('Ctrl+↵')
  })
})
