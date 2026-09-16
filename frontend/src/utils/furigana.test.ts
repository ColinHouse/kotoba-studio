import { describe, expect, it } from 'vitest'
import { furigana } from './furigana'

describe('furigana', () => {
  it('annotates only the kanji core, leaving okurigana alone', () => {
    expect(furigana('奢る', 'おごる')).toEqual([{ text: '奢', ruby: 'おご' }, { text: 'る' }])
  })

  it('annotates a whole compound', () => {
    expect(furigana('勉強', 'べんきょう')).toEqual([{ text: '勉強', ruby: 'べんきょう' }])
    expect(furigana('今日', 'きょう')).toEqual([{ text: '今日', ruby: 'きょう' }])
  })

  it('handles a kana prefix as well as a suffix', () => {
    expect(furigana('お願い', 'おねがい')).toEqual([
      { text: 'お' },
      { text: '願', ruby: 'ねが' },
      { text: 'い' },
    ])
  })

  it('accepts katakana readings', () => {
    expect(furigana('俺', 'オレ')).toEqual([{ text: '俺', ruby: 'おれ' }])
  })

  it('returns the word unannotated when there is nothing to annotate', () => {
    expect(furigana('しょうがない', 'しょうがない')).toEqual([{ text: 'しょうがない' }])
    expect(furigana('奢る', '')).toEqual([{ text: '奢る' }])
    expect(furigana('', 'おごる')).toEqual([])
  })
})
