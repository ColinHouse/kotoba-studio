import { readFileSync } from 'node:fs'
import { globSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

/**
 * The design system encodes learning state in ink density, so contrast is not
 * decoration here — it is information. These tests parse the tokens out of
 * style.css and hold each tier to the threshold for the size it is actually
 * used at.
 *
 * The four tiers exist for the *sentence*, which renders at 24px (30px on
 * desktop) — WCAG 2.1 "large text", so the bar there is 3:1. The top two tiers
 * are also used for ordinary small text, so they are held to 4.5:1. The lower
 * two must therefore never appear on small text; the last test enforces that,
 * because it is the only thing keeping the 3:1 allowance honest.
 */
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

const SURFACES = ['bg', 'surface', 'paper'] as const
const THEMES = [
  ['light', light],
  ['dark', dark],
] as const

describe('ink contrast', () => {
  it.each(THEMES)('%s: text tiers clear AA for small text (4.5:1)', (_name, p) => {
    for (const background of SURFACES) {
      for (const ink of ['ink', 'ink-70'] as const) {
        expect(ratio(p[ink]!, p[background]!), `${ink} on ${background}`).toBeGreaterThanOrEqual(
          4.5,
        )
      }
    }
  })

  it.each(THEMES)('%s: sentence tiers clear AA for large text (3:1)', (_name, p) => {
    for (const background of SURFACES) {
      for (const ink of ['ink-50', 'ink-35'] as const) {
        expect(ratio(p[ink]!, p[background]!), `${ink} on ${background}`).toBeGreaterThanOrEqual(3)
      }
    }
  })

  it.each(THEMES)('%s: the four tiers stay ordered, lightest last', (_name, p) => {
    const onPaper = (['ink', 'ink-70', 'ink-50', 'ink-35'] as const).map((ink) =>
      ratio(p[ink]!, p['paper']!),
    )
    for (let i = 1; i < onPaper.length; i++) {
      expect(onPaper[i]!, `tier ${i} must be lighter than tier ${i - 1}`).toBeLessThan(
        onPaper[i - 1]!,
      )
    }
  })
})

/**
 * The 3:1 allowance above is only legitimate while these tiers stay on the
 * sentence. Pair one with a small size and it becomes small text that fails AA.
 */
describe('the lower two tiers stay off small text', () => {
  // Every step of the type scale is below 24px, so anything wearing one is
  // small text; the bare `text-*` sizes are what the scale has not absorbed yet.
  const SMALL = /\btype-(body|note|meta|micro)\b|text-(xs|sm|\[(\d|1\d|2[0-3])px\])/

  it('no class list pairs ink-50 or ink-35 with a size below 24px', () => {
    // The legend under the sentence names the ink levels ("浅墨 = 已掌握") and
    // paints each sample in the level it names. A swatch that does not match the
    // thing it describes is worse than a faint one, so it stays as it is.
    const SWATCH = 'font-light text-ink-50'
    const offenders: string[] = []
    for (const file of globSync('src/**/*.vue')) {
      const source = readFileSync(file, 'utf8')
      for (const match of source.matchAll(/class="([^"]*text-ink-(?:50|35)[^"]*)"/g)) {
        if (match[1] === SWATCH) continue
        if (SMALL.test(match[1]!)) offenders.push(`${file}: ${match[1]!.slice(0, 70)}`)
      }
    }
    expect(offenders, `${offenders.length} small-text uses of the sentence tiers`).toEqual([])
  })
})
