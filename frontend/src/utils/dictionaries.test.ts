import { describe, expect, it } from 'vitest'
import {
  dictionaryCountLabel,
  dictionaryKindLabel,
  dictionaryListShows,
  originLabel,
  senseOrigin,
} from './dictionaries'

describe('dictionary labels', () => {
  it('names the kinds and counts what they hold', () => {
    expect(dictionaryKindLabel('jmdict')).toBe('JMdict')
    expect(dictionaryKindLabel('yomitan')).toBe('Yomitan 词典')
    expect(dictionaryKindLabel('yomitan-freq')).toBe('频率表')
    expect(
      dictionaryCountLabel({
        title: '频率表',
        kind: 'yomitan-freq',
        entry_count: 2000,
        revision: null,
        attribution: null,
      }),
    ).toBe('2,000 条频率')
    expect(
      dictionaryCountLabel({
        title: '词典',
        kind: 'yomitan',
        entry_count: 300,
        revision: null,
        attribution: null,
      }),
    ).toBe('300 条词条')
  })

  it('shows the list even when JMdict itself is not installed', () => {
    expect(
      dictionaryListShows([
        {
          title: '测试日中词典',
          kind: 'yomitan',
          entry_count: 2,
          revision: null,
          attribution: null,
        },
      ]),
    ).toBe(true)
    expect(dictionaryListShows([])).toBe(false)
    expect(dictionaryListShows(undefined)).toBe(false)
  })
})

describe('senseOrigin', () => {
  it('records the dictionary the gloss came from, not a hardcoded jmdict', () => {
    expect(senseOrigin({ dict_title: '测试日中词典', dict_kind: 'yomitan' }, false)).toBe(
      '测试日中词典',
    )
    expect(senseOrigin({ dict_title: 'JMdict (eng)', dict_kind: 'jmdict' }, false)).toBe(
      'JMdict (eng)',
    )
    expect(
      senseOrigin({ dict_title: 'A very long dictionary title', dict_kind: 'yomitan' }, false),
    ).toBe('yomitan')
    expect(senseOrigin(null, false)).toBe('jmdict')
    expect(senseOrigin({ dict_title: '测试日中词典', dict_kind: 'yomitan' }, true)).toBe('user')
  })
})

describe('originLabel', () => {
  it('maps known origins and passes titles through', () => {
    expect(originLabel('jmdict')).toBe('JMdict')
    expect(originLabel('user')).toBe('自填')
    expect(originLabel('yomitan')).toBe('Yomitan 词典')
    expect(originLabel('测试日中词典')).toBe('测试日中词典')
  })
})
