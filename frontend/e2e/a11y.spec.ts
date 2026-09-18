import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

/**
 * Accessibility baseline (#76): record what axe finds on the main pages today,
 * then fail when a *new* kind of violation appears. This is a ratchet, not a
 * clean bill of health — the known findings and the options for them are in the
 * issue and docs/conventions.md.
 *
 * The assertion is a subset check, deliberately. An exact match would fail the
 * build the moment someone *fixed* one of these, which is the opposite of what a
 * ratchet is for; clearing an entry means deleting it from BASELINE, and until
 * then a shrinking list still passes.
 *
 * `color-contrast` survives the ink-ramp work because the ochre accent (#b68235)
 * sits at 3.02:1 as small text. Every ink tier now clears its threshold; the
 * accent is a brand decision and has not been taken.
 */
const PAGES = ['/', '/inbox', '/review', '/library']

const BASELINE: Record<string, string[]> = {
  main: ['color-contrast', 'link-in-text-block'],
}

test('main pages introduce no axe violation beyond the recorded baseline', async ({ page }) => {
  const found = new Set<string>()
  for (const path of PAGES) {
    await page.goto(path)
    const { violations } = await new AxeBuilder({ page }).analyze()
    for (const violation of violations) found.add(violation.id)
  }
  const ids = [...found].sort()
  const unexpected = ids.filter((id) => !BASELINE.main.includes(id))
  expect(unexpected, 'axe found a kind of violation that is not in the baseline').toEqual([])
  const cleared = BASELINE.main.filter((id) => !ids.includes(id))
  if (cleared.length) {
    console.warn(`baseline entries no longer found, delete them: ${cleared.join(', ')}`)
  }
})
