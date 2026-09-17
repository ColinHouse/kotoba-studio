import { expect, test } from '@playwright/test'

/**
 * One smoke path: source → subtitle import → inbox picks a word → review
 * answers it → the card's due date moves. No dictionary, no AI, no network;
 * the term editor accepts a hand-written gloss when there is no candidate.
 */
const SRT = `1
00:00:01,000 --> 00:00:03,000
猫が好きです

2
00:00:04,000 --> 00:00:06,000
今日は寒いですね
`

test('capture to review moves the card due date', async ({ page, request }) => {
  const source = await request.post('/api/sources', {
    data: { title: 'E2E 冒烟作品', kind: 'anime' },
  })
  expect(source.ok()).toBeTruthy()
  const sourceId = (await source.json()).id as number

  const imported = await request.post(`/api/sources/${sourceId}/subtitles`, {
    multipart: {
      file: { name: 'e2e.srt', mimeType: 'text/plain', buffer: Buffer.from(SRT, 'utf-8') },
    },
  })
  expect(imported.ok()).toBeTruthy()
  expect((await imported.json()).created).toBe(2)

  // Inbox: open the line, pick the word, fill in the meaning, make the card.
  await page.goto('/inbox')
  await page.getByText('猫が好きです').click()
  // The token chip carries the dictionary form in its title: 猫（ねこ）…
  const word = page.locator('button[title^="猫（"]')
  await expect(word).toBeVisible()
  await word.click()
  await expect(page.locator('#term-headword')).toBeVisible()
  await page.locator('#term-gloss-zh').fill('猫')
  await page.getByRole('button', { name: '确认并建卡' }).click()

  // A kanji word defaults to a reading card and a cloze card.
  await expect
    .poll(async () => {
      const cards = await (await request.get('/api/cards')).json()
      return cards.length as number
    })
    .toBe(2)

  // Review on this device, keyboard only — no click anywhere. The wait is for
  // the card to render; Space reveals, 3 rates; focus visibility comes from the
  // global :focus-visible rule.
  await page.goto('/review')
  await expect(page.getByRole('button', { name: /显示答案/ })).toBeVisible()
  await page.keyboard.press('Space')
  await page.keyboard.press('3')

  // The answer went through FSRS: exactly the rated new card now has a due date.
  await expect
    .poll(async () => {
      const cards = await (await request.get('/api/cards')).json()
      return cards.filter((card: { due: string | null }) => card.due !== null).length as number
    })
    .toBe(1)
})
