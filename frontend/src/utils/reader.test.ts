import { describe, expect, it } from 'vitest'
import {
  arrowTurn,
  boxInk,
  boxStyle,
  isTypingTarget,
  lineInk,
  SWIPE_MIN,
  swipeTurn,
} from './reader'

describe('arrowTurn', () => {
  it('reads right to left by default: left arrow goes forward', () => {
    expect(arrowTurn(true, 'ArrowLeft')).toBe('next')
    expect(arrowTurn(true, 'ArrowRight')).toBe('prev')
  })

  it('reverses for left-to-right content', () => {
    expect(arrowTurn(false, 'ArrowRight')).toBe('next')
    expect(arrowTurn(false, 'ArrowLeft')).toBe('prev')
  })

  it('ignores other keys', () => {
    expect(arrowTurn(true, 'ArrowUp')).toBeNull()
    expect(arrowTurn(true, 'a')).toBeNull()
  })
})

describe('swipeTurn', () => {
  it('turns the page on a long horizontal drag', () => {
    expect(swipeTurn(true, 80)).toBe('next')
    expect(swipeTurn(true, -80)).toBe('prev')
    expect(swipeTurn(false, 80)).toBe('prev')
    expect(swipeTurn(false, -80)).toBe('next')
  })

  it('ignores short drags and mostly-vertical ones', () => {
    expect(swipeTurn(true, SWIPE_MIN - 1)).toBeNull()
    expect(swipeTurn(true, 80, 100)).toBeNull()
  })
})

describe('boxStyle', () => {
  it('turns image pixels into percentages of the page', () => {
    const style = boxStyle([100, 200, 200, 400], { width: 1000, height: 2000 })
    expect(style).toEqual({ left: '10%', top: '10%', width: '10%', height: '10%' })
  })

  it('returns nothing until the image size is known', () => {
    expect(boxStyle([0, 0, 10, 10], { width: 0, height: 0 })).toEqual({})
  })
})

describe('ink classes', () => {
  it('darkens a block once a card was built from it', () => {
    expect(boxInk({ card_count: 0 })).toBe('reader-box')
    expect(boxInk({ card_count: 2 })).toBe('reader-box reader-box-carded')
    expect(lineInk({ card_count: 1 })).toBe('reader-line reader-line-carded')
  })
})

describe('isTypingTarget', () => {
  it('protects form fields and contenteditable', () => {
    expect(isTypingTarget({ tagName: 'INPUT' })).toBe(true)
    expect(isTypingTarget({ tagName: 'textarea' })).toBe(true)
    expect(isTypingTarget({ tagName: 'BUTTON', isContentEditable: true })).toBe(true)
    expect(isTypingTarget({ tagName: 'BUTTON' })).toBe(false)
    expect(isTypingTarget(null)).toBe(false)
  })
})
