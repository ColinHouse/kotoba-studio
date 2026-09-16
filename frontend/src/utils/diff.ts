/** Answer-vs-expected diff, ported from vocab_test's highlight logic: split into CJK / kana / latin / punctuation runs. */
export interface DiffPiece {
  text: string
  ok: boolean
  extra?: boolean
  missing?: boolean
}

const TOKEN = /[一-鿿]+|[ぁ-ゖァ-ヶー]+|[\w]+|[^\w\s]/gu

export function splitUnits(s: string): string[] {
  return s.match(TOKEN) ?? []
}

export function diffAnswer(given: string, expected: string): DiffPiece[] {
  const g = splitUnits(given)
  const e = splitUnits(expected)
  const out: DiffPiece[] = []
  const n = Math.max(g.length, e.length)
  for (let i = 0; i < n; i++) {
    const gu = g[i]
    const eu = e[i]
    if (gu !== undefined && eu !== undefined) {
      out.push({ text: eu, ok: gu === eu })
    } else if (eu !== undefined) {
      out.push({ text: eu, ok: false, missing: true })
    } else if (gu !== undefined) {
      out.push({ text: gu, ok: false, extra: true })
    }
  }
  return out
}
