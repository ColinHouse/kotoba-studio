import { describe, expect, it } from 'vitest'
import { kanjiInk, kanjiStatusLabel } from './kanji'

describe('kanjiInk', () => {
  it('darkens as mastery grows', () => {
    expect(kanjiInk('unseen')).toBe('text-ink-35')
    expect(kanjiInk('seen')).toBe('text-ink-50')
    expect(kanjiInk('learning')).toBe('text-ink-70')
    expect(kanjiInk('mastered')).toBe('text-ink')
  })
})

describe('kanjiStatusLabel', () => {
  it('labels every status in Chinese', () => {
    expect(kanjiStatusLabel('unseen')).toBe('未见过')
    expect(kanjiStatusLabel('mastered')).toBe('已掌握')
  })
})
