import { describe, expect, it } from 'vitest'
import { coverageInk, coveragePercent } from './coverage'

describe('coveragePercent', () => {
  it('rounds to whole percent', () => {
    expect(coveragePercent(0)).toBe('0%')
    expect(coveragePercent(1 / 3)).toBe('33%')
    expect(coveragePercent(0.785)).toBe('79%')
    expect(coveragePercent(1)).toBe('100%')
  })
})

describe('coverageInk', () => {
  it('darkens as coverage grows', () => {
    expect(coverageInk(0)).toBe('text-ink-35')
    expect(coverageInk(0.01)).toBe('text-ink-50')
    expect(coverageInk(0.6)).toBe('text-ink-70')
    expect(coverageInk(0.85)).toBe('text-ink')
    expect(coverageInk(1)).toBe('text-ink')
  })
})
