import { describe, expect, it } from 'vitest'
import { hasKanji, kanaEqual, toHiragana, toKatakana } from './kana'

describe('kana', () => {
  it('converts scripts', () => {
    expect(toHiragana('キョウ')).toBe('きょう')
    expect(toKatakana('おごる')).toBe('オゴル')
  })
  it('compares readings ignoring script, width and spaces', () => {
    expect(kanaEqual('オゴル', 'おごる')).toBe(true)
    expect(kanaEqual('きょう ', 'ｷｮｳ')).toBe(true)
    expect(kanaEqual('おごる', 'おこる')).toBe(false)
  })
  it('detects kanji', () => {
    expect(hasKanji('奢る')).toBe(true)
    expect(hasKanji('おごる')).toBe(false)
  })
})
