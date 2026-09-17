import {
  BasicLearningStepsStrategy,
  createEmptyCard,
  fsrs,
  generatorParameters,
  Rating,
  State,
  StrategyMode,
  type Card as TsCard,
  type TLearningStepsStrategy,
} from 'ts-fsrs'

/**
 * Offline scheduling with ts-fsrs, mirroring the backend (ADR 0004).
 *
 * The backend (py-fsrs) and this library are sibling implementations. Three
 * differences are handled here rather than papered over:
 *
 * - Hard on a later learning step: py-fsrs repeats that step's interval,
 *   ts-fsrs averages the first two. The strategy below restores py-fsrs's rule,
 *   which the parity test pins.
 * - py-fsrs fuzzes intervals by default to spread due dates out; the exact
 *   fuzz draw cannot be reproduced across implementations, so the client
 *   computes the unfuzzed schedule. The server replays and re-fuzzes anyway.
 * - py-fsrs counts a review as "same day" by exact 24-hour multiples, ts-fsrs
 *   by UTC calendar dates. A gap under 24h that crosses midnight therefore
 *   schedules a day differently; that boundary is left to the server.
 */

/** Learning/relearning step units ("1m", "10m", "1h", "1d") as minutes. */
function stepMinutes(step: string | number): number {
  if (typeof step === 'number') return step
  const value = parseInt(step.slice(0, -1), 10)
  const unit = step.slice(-1)
  return unit === 'm' ? value : unit === 'h' ? value * 60 : value * 1440
}

const pyFsrsLearningSteps: TLearningStepsStrategy = (params, state, curStep) => {
  const result = BasicLearningStepsStrategy(params, state, curStep) ?? {}
  if (state === State.Review || !result[Rating.Hard]) return result
  const steps = state === State.Relearning ? params.relearning_steps : params.learning_steps
  let minutes: number
  if (curStep === 0 && steps.length === 1) {
    minutes = Math.round(stepMinutes(steps[0]!) * 1.5)
  } else if (curStep === 0 && steps.length >= 2) {
    minutes = Math.round((stepMinutes(steps[0]!) + stepMinutes(steps[1]!)) / 2)
  } else {
    minutes = Math.round(stepMinutes(steps[Math.min(curStep, steps.length - 1)]!))
  }
  result[Rating.Hard] = { scheduled_minutes: minutes, next_step: curStep }
  return result
}

/** The FSRS fields the backend persists on a card (models.Review.Card). */
export interface CardState {
  state: number
  step: number | null
  stability: number | null
  difficulty: number | null
  due: string | null
  last_review: string | null
}

export interface FsrsSettings {
  desired_retention?: number | null
  fsrs_parameters?: number[] | null
}

const RATINGS = { 1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Easy } as const

export function makeScheduler(settings: FsrsSettings = {}) {
  const f = fsrs(
    generatorParameters({
      request_retention: settings.desired_retention ?? 0.9,
      ...(settings.fsrs_parameters?.length ? { w: [...settings.fsrs_parameters] } : {}),
    }),
  )
  return f.useStrategy(StrategyMode.LEARNING_STEPS, pyFsrsLearningSteps)
}

function toTsCard(card: CardState, now: Date): TsCard {
  return {
    ...createEmptyCard(now),
    due: card.due ? new Date(card.due) : now,
    stability: card.stability ?? 0,
    difficulty: card.difficulty ?? 0,
    state: card.state,
    learning_steps: card.step ?? 0,
    last_review: card.last_review ? new Date(card.last_review) : undefined,
  }
}

/** Apply one rating locally; returns the same shape the backend persists. */
export function scheduleRating(
  card: CardState,
  rating: 1 | 2 | 3 | 4,
  now: Date,
  settings: FsrsSettings = {},
): CardState {
  const next = makeScheduler(settings).next(toTsCard(card, now), now, RATINGS[rating]).card
  return {
    state: next.state,
    step: next.state === 2 ? null : next.learning_steps,
    stability: next.stability,
    difficulty: next.difficulty,
    due: next.due.toISOString(),
    last_review: next.last_review ? next.last_review.toISOString() : null,
  }
}
