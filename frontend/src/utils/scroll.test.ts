import { describe, expect, it } from 'vitest'
import { followsNewest } from './scroll'

describe('followsNewest', () => {
  it('follows when the viewport is at the bottom', () => {
    expect(followsNewest(800, 200, 1000)).toBe(true)
  })

  it('follows when it is within the tolerance of the bottom', () => {
    expect(followsNewest(760, 200, 1000)).toBe(true)
  })

  it('does not follow once the user has scrolled up to read', () => {
    expect(followsNewest(400, 200, 1000)).toBe(false)
    expect(followsNewest(0, 200, 1000)).toBe(false)
  })

  it('treats a content-less viewport as following', () => {
    expect(followsNewest(0, 200, 200)).toBe(true) // scrollHeight == clientHeight
  })
})
