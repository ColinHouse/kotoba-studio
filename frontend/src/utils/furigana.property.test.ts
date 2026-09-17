import { describe, expect, it } from 'vitest'
import fc from 'fast-check'
import { furigana } from './furigana'

/**
 * The reading may be wrong, but the word itself must survive: joining the
 * segment bases has to give back exactly the word that was passed in.
 * (Property tests live here rather than with the backend's hypothesis suite
 * because `furigana` is a frontend function; see issue #71.)
 */
const CHARS = [
  ...'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん',
  ...'がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽっゃゅょゎー',
  ...'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワオン',
  ...'漢字日本語猫犬辛奢願',
]

const jp = fc.string({ unit: fc.constantFrom(...CHARS), maxLength: 10 })

describe('furigana properties', () => {
  it('always spells the word back out when the segments are joined', () => {
    const details = fc.check(
      fc.property(jp, jp, (word, reading) => {
        const joined = furigana(word, reading)
          .map((segment) => segment.text)
          .join('')
        return joined === word.trim()
      }),
      { numRuns: 300 },
    )
    expect(details.failed, `counterexample: ${JSON.stringify(details.counterexample)}`).toBe(false)
  })
})
