import { describe, expect, it } from 'vitest'
import { scheduleRating, type CardState, type FsrsSettings } from './fsrs'

/**
 * Parity fixtures generated with the backend's own library
 * (py-fsrs 6.x, `Scheduler(..., enable_fuzzing=False)`) on 2026-09-01 12:00 UTC.
 * Reviews are spaced in exact 24-hour multiples so both libraries agree on
 * "days since last review" (see the note in fsrs.ts).
 */
const BASE = new Date('2026-09-01T12:00:00Z')

interface Step {
  due: string
  state: number
  step: number | null
  stability: number
  difficulty: number
}

const FRESH: CardState = {
  state: 1,
  step: null,
  stability: null,
  difficulty: null,
  due: BASE.toISOString(),
  last_review: null,
}

const DEFAULT_STEPS: Step[] = [
  {
    due: '2026-09-01T12:10:00+00:00',
    state: 1,
    step: 1,
    stability: 2.3065,
    difficulty: 2.118103970459016,
  },
  {
    due: '2026-09-09T12:00:00+00:00',
    state: 2,
    step: null,
    stability: 7.31530074407728,
    difficulty: 2.111214235785395,
  },
  {
    due: '2026-09-05T12:10:00+00:00',
    state: 3,
    step: 0,
    stability: 1.1480449426584476,
    difficulty: 7.392238132342694,
  },
  {
    due: '2026-09-22T12:00:00+00:00',
    state: 2,
    step: null,
    stability: 7.8102685021759495,
    difficulty: 7.38007426350719,
  },
]

const CUSTOM_W = [
  0.4, 1.2, 3.5, 9.0, 5.0, 0.8, 3.0, 0.001, 1.5, 0.2, 0.8, 1.5, 0.06, 0.25, 1.6, 0.6, 1.8, 0.5,
  0.09, 0.07, 0.15,
]

const CUSTOM_STEPS: Step[] = [
  {
    due: '2026-09-01T12:10:00+00:00',
    state: 1,
    step: 1,
    stability: 3.5,
    difficulty: 1.046967575604885,
  },
  {
    due: '2026-09-02T12:10:00+00:00',
    state: 1,
    step: 1,
    stability: 5.725994578804836,
    difficulty: 4.0222572289722125,
  },
  {
    due: '2026-09-04T12:01:00+00:00',
    state: 1,
    step: 0,
    stability: 0.9046151541321813,
    difficulty: 7.994388480867106,
  },
  {
    due: '2026-10-03T12:00:00+00:00',
    state: 2,
    step: null,
    stability: 6.5085291054532695,
    difficulty: 7.313502280134344,
  },
]

function scheduleAll(
  offsets: number[],
  ratings: (1 | 2 | 3 | 4)[],
  settings: FsrsSettings = {},
): CardState[] {
  let card = FRESH
  return offsets.map((offset, i) => {
    card = scheduleRating(
      card,
      ratings[i]!,
      new Date(BASE.getTime() + offset * 86_400_000),
      settings,
    )
    return card
  })
}

describe('offline fsrs scheduling', () => {
  it('matches the backend schedule with default parameters', () => {
    const cards = scheduleAll([0, 1, 4, 13], [3, 3, 1, 3])
    expect(cards).toHaveLength(DEFAULT_STEPS.length)
    DEFAULT_STEPS.forEach((step, i) => {
      const card = cards[i]!
      expect(new Date(card.due!).getTime()).toBe(new Date(step.due).getTime())
      expect(card.state).toBe(step.state)
      expect(card.step).toBe(step.step)
      expect(card.stability!).toBeCloseTo(step.stability, 6)
      expect(card.difficulty!).toBeCloseTo(step.difficulty, 6)
    })
  })

  it('forwards personalized parameters and desired retention', () => {
    const cards = scheduleAll([0, 1, 3, 10], [3, 2, 1, 4], {
      desired_retention: 0.8,
      fsrs_parameters: CUSTOM_W,
    })
    expect(cards).toHaveLength(CUSTOM_STEPS.length)
    CUSTOM_STEPS.forEach((step, i) => {
      const card = cards[i]!
      expect(new Date(card.due!).getTime()).toBe(new Date(step.due).getTime())
      expect(card.state).toBe(step.state)
      expect(card.step).toBe(step.step)
      expect(card.stability!).toBeCloseTo(step.stability, 6)
      expect(card.difficulty!).toBeCloseTo(step.difficulty, 6)
    })
  })
})
