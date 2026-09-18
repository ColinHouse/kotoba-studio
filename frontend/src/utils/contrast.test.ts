import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

/**
 * The design system encodes learning state in ink density, so contrast is not
 * decoration here — it is information. These tests parse the tokens out of
 * style.css and pin which combinations fall short of WCAG 2.1 AA (4.5:1) on
 * purpose, so a token change that improves or worsens them is a deliberate edit
 * to this table, not a silent drift.
 *
 * Measured (2026-09): light ink-50 is 3.55–4.13 and ink-35 is 2.38–2.77 across
 * bg/surface/paper; dark ink-35 is 3.60–4.12. Everything else clears AA.
 * Recommendations live in the issue (#76), not in this file.
 */
// vitest runs with the frontend directory as cwd; import.meta.url is not a
// file: URL under the happy-dom environment, so read the file by path.
const css = readFileSync('src/style.css', 'utf8')

type Palette = Record<string, string>

function palette(marker: string): Palette {
  const start = css.indexOf(marker)
  expect(start, `token block not found: ${marker}`).toBeGreaterThan(-1)
  const body = css.slice(start, css.indexOf('}', start))
  const out: Palette = {}
  for (const match of body.matchAll(/--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})/g)) {
    out[match[1]!] = match[2]!
  }
  return out
}

const light = palette(':root {')
const dark = palette(":root[data-theme='dark'] {")

function luminance(hex: string): number {
  const channels = [1, 3, 5]
    .map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
  return 0.2126 * channels[0]! + 0.7152 * channels[1]! + 0.0722 * channels[2]!
}

function ratio(foreground: string, background: string): number {
  const a = luminance(foreground)
  const b = luminance(background)
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}

const INKS = ['ink', 'ink-70', 'ink-50', 'ink-35'] as const
/**
 * The two page papers. `--surface` is hover and skeleton furniture, not a text
 * background for state tokens, so it is deliberately not part of the AA
 * guarantee — the axe run on the rendered pages is the independent check.
 */
const BACKGROUNDS = ['bg', 'paper'] as const

function failures(p: Palette): string[] {
  return BACKGROUNDS.flatMap((background) =>
    INKS.filter((ink) => ratio(p[ink]!, p[background]!) < 4.5).map(
      (ink) => `${ink} on ${background}`,
    ),
  )
}

describe('ink contrast (WCAG 2.1 AA, 4.5:1)', () => {
  it('the reading levels clear AA on every layer, in both themes', () => {
    for (const p of [light, dark]) {
      for (const background of BACKGROUNDS) {
        expect(ratio(p['ink']!, p[background]!), `ink on ${background}`).toBeGreaterThanOrEqual(4.5)
        expect(
          ratio(p['ink-70']!, p[background]!),
          `ink-70 on ${background}`,
        ).toBeGreaterThanOrEqual(4.5)
      }
    }
  })

  it('leaves no state level below AA in either theme (#164)', () => {
    expect(failures(light)).toEqual([])
    expect(failures(dark)).toEqual([])
  })

  it('keeps the four levels ordered: 未学最重 → 学习中 → 已掌握 → 已忽略最轻', () => {
    const lightRamp = INKS.map((ink) => luminance(light[ink]!))
    const darkRamp = INKS.map((ink) => luminance(dark[ink]!))
    // light paper: emphasis falls as luminance rises; ink paper: the reverse.
    expect([...lightRamp].sort((a, b) => a - b)).toEqual(lightRamp)
    expect([...darkRamp].sort((a, b) => b - a)).toEqual(darkRamp)
  })
})
