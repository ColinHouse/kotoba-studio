/** Apple platforms show ⌘ in shortcut hints; everything else shows Ctrl. */

export function isMac(userAgent: string): boolean {
  return /Macintosh|iPhone|iPad|iPod/.test(userAgent)
}

export function commandKey(userAgent: string): string {
  return isMac(userAgent) ? '⌘' : 'Ctrl'
}

export function confirmShortcut(userAgent: string): string {
  return isMac(userAgent) ? '⌘↵' : 'Ctrl+↵'
}
