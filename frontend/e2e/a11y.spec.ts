import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

/**
 * Accessibility ratchet (#76, repaired in #164): a *new* kind of axe violation
 * on the main pages fails the test; fixing one means deleting it here. It is a
 * subset check, not an exact match — an exact match meant that fixing anything
 * the baseline recorded turned the test red.
 *
 * `color-contrast` stays on the list for the gold accent, which is reserved for
 * actions and can only change by a design decision. The four ink levels that
 * encode learning state were fixed in #164 and are verified numerically in
 * `src/utils/contrast.test.ts`.
 */
const PAGES = ['/', '/inbox', '/review', '/library']

const BASELINE = ['color-contrast', 'link-in-text-block']

test('main pages introduce no axe violation beyond the recorded baseline', async ({ page }) => {
  const found = new Set<string>()
  for (const path of PAGES) {
    await page.goto(path)
    const { violations } = await new AxeBuilder({ page }).analyze()
    for (const violation of violations) found.add(violation.id)
  }
  const unexpected = [...found].filter((id) => !BASELINE.includes(id)).sort()
  expect(unexpected).toEqual([])
})
