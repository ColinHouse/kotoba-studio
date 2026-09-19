import { describe, expect, it } from 'vitest'
import { relSeconds } from './format'

const NOW = new Date('2026-09-19T12:00:00Z')

describe('relSeconds', () => {
  it('counts seconds first, so a live feed looks alive', () => {
    expect(relSeconds('2026-09-19T11:59:58Z', NOW)).toBe('2 秒前')
    expect(relSeconds('2026-09-19T11:59:30Z', NOW)).toBe('30 秒前')
  })

  it('steps up to minutes, hours and days', () => {
    expect(relSeconds('2026-09-19T11:55:00Z', NOW)).toBe('5 分钟前')
    expect(relSeconds('2026-09-19T09:00:00Z', NOW)).toBe('3 小时前')
    expect(relSeconds('2026-09-17T12:00:00Z', NOW)).toBe('2 天前')
  })

  it('never goes negative when the clock runs ahead of the timestamp', () => {
    expect(relSeconds('2026-09-19T12:00:05Z', NOW)).toBe('0 秒前')
  })
})
