import { describe, expect, it } from 'vitest'
import type { Source } from '@/api/types'
import { checklistVisible, setupProgress } from './setup'

function source(overrides: Partial<Source> = {}): Source {
  return {
    id: 1,
    title: '作品',
    title_ja: null,
    kind: 'game',
    region: null,
    window: null,
    created_at: '2026-09-01T00:00:00Z',
    line_count: 0,
    term_count: 0,
    known_term_count: 0,
    ...overrides,
  }
}

const region = { left: 0, top: 0, width: 100, height: 50, display: 0 }

describe('first-run checklist', () => {
  it('shows on a fresh install', () => {
    const progress = setupProgress(false, [], 0, false)
    expect(progress.allDone).toBe(false)
    expect(checklistVisible(progress, false)).toBe(true)
  })

  it('stays visible while the user sets things up in the checklist itself', () => {
    // A bare source is what step two creates; it must not count as "established".
    const progress = setupProgress(true, [source({ region })], 0, false)
    expect(checklistVisible(progress, false)).toBe(true)
  })

  it('hides itself once all three steps are done, without being dismissed', () => {
    const progress = setupProgress(true, [source({ region, line_count: 3 })], 0, false)
    expect(progress.allDone).toBe(true)
    expect(checklistVisible(progress, false)).toBe(false)
  })

  it('treats a connected hook as the line source', () => {
    const progress = setupProgress(true, [source({ region })], 0, true)
    expect(progress.lines).toBe(true)
    expect(progress.allDone).toBe(true)
  })

  it('does not bother an established user (cards or lines)', () => {
    expect(checklistVisible(setupProgress(false, [], 5, false), false)).toBe(false)
    const withLines = setupProgress(false, [source({ line_count: 1 })], 0, false)
    expect(withLines.established).toBe(true)
    expect(checklistVisible(withLines, false)).toBe(false)
  })

  it('stays hidden once dismissed', () => {
    const progress = setupProgress(false, [], 0, false)
    expect(checklistVisible(progress, true)).toBe(false)
  })
})
