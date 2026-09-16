import { describe, expect, it } from 'vitest'
import { originLabel, senseOrigin } from './dictionaries'

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
