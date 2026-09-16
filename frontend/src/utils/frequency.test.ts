import { describe, expect, it } from 'vitest'
import { byFrequency, frequencyBand } from './frequency'

describe('frequencyBand', () => {
  it('maps ranks to bands at the boundaries', () => {
    expect(frequencyBand(1).label).toBe('常用')
    expect(frequencyBand(1500).label).toBe('常用')
    expect(frequencyBand(1501).label).toBe('次常用')
    expect(frequencyBand(5000).label).toBe('次常用')
    expect(frequencyBand(5001).label).toBe('较少见')
    expect(frequencyBand(15000).label).toBe('较少见')
    expect(frequencyBand(15001).label).toBe('罕见')
  })

  it('treats a missing rank as rare', () => {
    expect(frequencyBand(null)).toEqual({ label: '罕见', className: 'text-ink-35' })
  })
})

describe('byFrequency', () => {
  const items = [
    { word: '鳥', frequency_rank: null },
    { word: '水', frequency_rank: 5000 },
    { word: '犬', frequency_rank: 10 },
    { word: '猫', frequency_rank: null },
  ]

  it('puts ranked words first by rank and unranked last', () => {
    expect(byFrequency(items).map((item) => item.word)).toEqual(['犬', '水', '鳥', '猫'])
  })

  it('does not mutate the input', () => {
    byFrequency(items)
    expect(items.map((item) => item.word)).toEqual(['鳥', '水', '犬', '猫'])
  })
})
