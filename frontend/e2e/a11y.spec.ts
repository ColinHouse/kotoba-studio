import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

/**
 * Accessibility baseline (#76): record what axe finds on the main pages today,
 * then fail when a *new* kind of violation appears. This is a ratchet, not a
 * clean bill of health — the known findings and the options for them are in the
 * issue and docs/conventions.md.
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
  expect(ids).toEqual(BASELINE.main)
})
