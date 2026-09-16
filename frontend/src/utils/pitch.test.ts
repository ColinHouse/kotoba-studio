import { describe, expect, it } from 'vitest'
import { pitchLevels, splitMorae } from './pitch'

describe('splitMorae', () => {
  it('merges small kana into the previous mora', () => {
    expect(splitMorae('きょう')).toEqual(['きょ', 'う'])
    expect(splitMorae('しゅう')).toEqual(['しゅ', 'う'])
    expect(splitMorae('コーヒー')).toEqual(['コ', 'ー', 'ヒ', 'ー'])
    expect(splitMorae('がっこう')).toEqual(['が', 'っ', 'こ', 'う'])
    expect(splitMorae('ｷｮｳ')).toEqual(['キョ', 'ウ'])
  })
})

describe('pitchLevels', () => {
  it('draws the four accent types over とうきょう', () => {
    expect(pitchLevels('とうきょう', 0)).toEqual([false, true, true, true]) // heiban
    expect(pitchLevels('とうきょう', 1)).toEqual([true, false, false, false]) // atamadaka
    expect(pitchLevels('とうきょう', 2)).toEqual([false, true, false, false]) // nakadaka
    expect(pitchLevels('とうきょう', 4)).toEqual([false, true, true, true]) // odaka
  })
})
