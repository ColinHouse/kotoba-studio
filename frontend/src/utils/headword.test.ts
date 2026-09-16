import { describe, expect, it } from 'vitest'
import type { DictEntry } from '@/api/types'
import { headwordFor } from './headword'

const entry = (kanji: string[], kana: string[], uk: boolean): DictEntry => ({
  id: '1',
  dict_id: 1,
  kanji,
  kana,
  senses: [],
  pos: [],
  common: true,
  is_expression: false,
  usually_kana: uk,
  headword: kanji[0] ?? kana[0]!,
  reading: kana[0] ?? '',
})

describe('headwordFor', () => {
  it('keeps kanji when the text used kanji', () => {
    expect(headwordFor(entry(['奢る'], ['おごる'], true), '奢っ', 'x')).toBe('奢る')
  })
  it('prefers kana for usually-kana entries written in kana', () => {
    expect(headwordFor(entry(['仕様がない'], ['しょうがない'], true), 'しょうがない', 'x')).toBe(
      'しょうがない',
    )
  })
  it('uses kanji for kana surfaces of normally-kanji words', () => {
    expect(headwordFor(entry(['俺'], ['おれ'], false), 'おれ', 'x')).toBe('俺')
    expect(headwordFor(undefined, 'おれ', 'fallback')).toBe('fallback')
  })
})
