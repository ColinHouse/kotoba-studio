import { isKanji, toHiragana } from './kana'

export interface RubySegment {
  /** Base text as written. */
  text: string
  /** Reading to set above it, when the base is kanji. */
  ruby?: string
}

/**
 * Split a word and its reading into ruby segments.
 *
 * Only the kanji core gets a reading: 奢る + おごる becomes 奢[おご] + る, so the
 * okurigana is not repeated above itself. Leading kana are handled the same way
 * (お願い + おねがい → お + 願[ねが] + い).
 *
 * This is deliberately conservative: when the two strings do not line up it
 * returns the word unannotated rather than guessing, because a wrong reading on
 * a review card is worse than no reading.
 */
export function furigana(word: string, reading: string): RubySegment[] {
  const base = word.trim()
  const kana = toHiragana((reading ?? '').trim())
  if (!base) return []
  if (!kana || ![...base].some(isKanji) || toHiragana(base) === kana) {
    return [{ text: base }]
  }

  const chars = [...base]
  const readingChars = [...kana]

  let prefix = 0
  while (
    prefix < chars.length &&
    prefix < readingChars.length &&
    !isKanji(chars[prefix]!) &&
    toHiragana(chars[prefix]!) === readingChars[prefix]
  ) {
    prefix += 1
  }

  let suffix = 0
  while (
    suffix < chars.length - prefix &&
    suffix < readingChars.length - prefix &&
    !isKanji(chars[chars.length - 1 - suffix]!) &&
    toHiragana(chars[chars.length - 1 - suffix]!) === readingChars[readingChars.length - 1 - suffix]
  ) {
    suffix += 1
  }

  const core = chars.slice(prefix, chars.length - suffix).join('')
  const coreReading = readingChars.slice(prefix, readingChars.length - suffix).join('')
  if (!core || !coreReading) return [{ text: base }]

  const segments: RubySegment[] = []
  if (prefix) segments.push({ text: chars.slice(0, prefix).join('') })
  segments.push({ text: core, ruby: coreReading })
  if (suffix) segments.push({ text: chars.slice(chars.length - suffix).join('') })
  return segments
}
