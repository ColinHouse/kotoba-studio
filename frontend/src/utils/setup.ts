import type { Source } from '@/api/types'

/** What the first-run checklist knows: three steps and whether the user is past it. */
export interface SetupProgress {
  dict: boolean
  region: boolean
  lines: boolean
  allDone: boolean
  /**
   * 有台词或有卡片 = 已经在用这个应用的人。
   * 「有作品」按有内容算：新用户在准备清单里就会建作品，只建了壳不算老用户，
   * 否则清单永远走不到第二步。
   */
  established: boolean
}

export function setupProgress(
  dictInstalled: boolean,
  sources: Source[],
  cardCount: number,
  hookConnected: boolean,
): SetupProgress {
  const dict = dictInstalled
  const region = sources.some((source) => source.region !== null || source.window?.region != null)
  const lines = hookConnected || sources.some((source) => source.line_count > 0)
  const established = cardCount > 0 || sources.some((source) => source.line_count > 0)
  return { dict, region, lines, allDone: dict && region && lines, established }
}

/** All three done hides it; a real user hides it; otherwise only a dismissal does. */
export function checklistVisible(progress: SetupProgress, dismissed: boolean): boolean {
  return !dismissed && !progress.allDone && !progress.established
}
