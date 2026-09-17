import { describe, expect, it } from 'vitest'
import {
  computeBarLayout,
  computePolylinePoints,
  computeRollingAccuracy,
  formatPercent,
} from './stats'

describe('stats utils', () => {
  it('formats percentages correctly', () => {
    expect(formatPercent(null)).toBe('—')
    expect(formatPercent(undefined)).toBe('—')
    expect(formatPercent(0.9)).toBe('90.0%')
    expect(formatPercent(0.8567)).toBe('85.7%')
    expect(formatPercent(0)).toBe('0.0%')
    expect(formatPercent(1.0)).toBe('100.0%')
  })

  it('computes bar layouts with boundary handling', () => {
    expect(computeBarLayout([], 100, 100)).toEqual([])

    const bars = computeBarLayout([10, 20, 0], 300, 100, { top: 0, right: 0, bottom: 0, left: 0 })
    expect(bars.length).toBe(3)
    expect(bars[0].width).toBeGreaterThan(0)
    expect(bars[0].height).toBe(50) // 10 / 20 * 100
    expect(bars[1].height).toBe(100) // 20 / 20 * 100
    expect(bars[2].height).toBe(0) // 0
  })

  it('computes rolling accuracy with empty periods', () => {
    expect(computeRollingAccuracy([])).toEqual([])

    const data = [
      { count: 10, correct: 9 }, // 90%
      { count: 10, correct: 8 }, // 17/20 = 85%
      { count: 0, correct: 0 },
      { count: 0, correct: 0 },
    ]
    const rolling = computeRollingAccuracy(data, 2)
    expect(rolling[0]).toBe(0.9)
    expect(rolling[1]).toBe(0.85)
    expect(rolling[2]).toBe(0.8) // (8+0)/(10+0) = 80%
    expect(rolling[3]).toBeNull() // (0+0)/(0+0) = null
  })

  it('generates svg polyline points skipping nulls', () => {
    expect(computePolylinePoints([], 100, 100)).toBe('')

    const points = computePolylinePoints([0.5, null, 1.0], 200, 100, {
      top: 0,
      right: 0,
      bottom: 0,
      left: 0,
    })
    const tokens = points.split(' ')
    expect(tokens.length).toBe(2) // null skipped
    expect(tokens[0]).toBe('0.0,50.0')
    expect(tokens[1]).toBe('200.0,0.0')
  })
})
