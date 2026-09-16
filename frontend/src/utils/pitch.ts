/** Mora splitting and pitch levels for drawing a pitch contour. */

const SMALL = new Set('ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ')

/** Small kana belong to the previous mora: きょ is one mora, しゅう is two. */
export function splitMorae(reading: string): string[] {
  const out: string[] = []
  for (const ch of reading.normalize('NFKC')) {
    if (SMALL.has(ch) && out.length) out[out.length - 1] += ch
    else out.push(ch)
  }
  return out
}

/** Which morae are high: 0 heiban, 1 atamadaka, n odaka, else nakadaka. */
export function pitchLevels(reading: string, accent: number): boolean[] {
  return splitMorae(reading).map((_, index) => {
    const position = index + 1
    if (accent === 0) return position >= 2
    if (accent === 1) return position === 1
    return position >= 2 && position <= accent
  })
}
