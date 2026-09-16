import { describe, expect, it } from 'vitest'
import { diffAnswer, splitUnits } from './diff'

describe('diff', () => {
  it('splits mixed text into units', () => {
    expect(splitUnits('今日は俺が奢ってやるよ。')).toEqual(['今日', 'は', '俺', 'が', '奢', 'ってやるよ', '。'])
  })
  it('marks wrong, missing and extra units', () => {
    const pieces = diffAnswer('おごる', 'おごって')
    expect(pieces).toEqual([{ text: 'おごって', ok: false }])
    const extra = diffAnswer('猫が好き。', '猫が好き')
    expect(extra.at(-1)).toEqual({ text: '。', ok: false, extra: true })
    const missing = diffAnswer('猫', '猫が好き')
    expect(missing.filter((p) => p.missing).length).toBe(3)
    expect(diffAnswer('同じ', '同じ').every((p) => p.ok)).toBe(true)
  })
})
