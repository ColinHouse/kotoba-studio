export function toHiragana(s: string): string {
  return s.replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60))
}

export function toKatakana(s: string): string {
  return s.replace(/[ぁ-ゖ]/g, (c) => String.fromCharCode(c.charCodeAt(0) + 0x60))
}

export function isKanji(ch: string): boolean {
  const cp = ch.codePointAt(0) ?? 0
  return (
    (cp >= 0x4e00 && cp <= 0x9fff) ||
    (cp >= 0x3400 && cp <= 0x4dbf) ||
    (cp >= 0xf900 && cp <= 0xfaff) ||
    (cp >= 0x20000 && cp <= 0x2fa1f) ||
    ch === '々' ||
    ch === '〆'
  )
}

export function hasKanji(s: string): boolean {
  return [...s].some(isKanji)
}

export function kanaEqual(a: string, b: string): boolean {
  const norm = (s: string) => toHiragana(s.normalize('NFKC').replace(/\s+/g, ''))
  return norm(a) === norm(b)
}
