/** 频率档位与排序。阈值只在这里定义，界面组件不要各写一份。 */

export interface FrequencyBand {
  label: string
  className: string
}

const BANDS: { max: number; label: string; className: string }[] = [
  { max: 1500, label: '常用', className: 'text-ink' },
  { max: 5000, label: '次常用', className: 'text-ink-70' },
  { max: 15000, label: '较少见', className: 'text-ink-50' },
]

const RARE: FrequencyBand = { label: '罕见', className: 'text-ink-35' }

/** Rank 1 is the most common word; no rank is as rare as it gets. */
export function frequencyBand(rank: number | null): FrequencyBand {
  if (rank === null) return RARE
  return BANDS.find((band) => rank <= band.max) ?? RARE
}

/** Rank ascending, words without a rank last (never treated as rank 0). */
export function byFrequency<T extends { frequency_rank: number | null }>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    if (a.frequency_rank === null) return b.frequency_rank === null ? 0 : 1
    if (b.frequency_rank === null) return -1
    return a.frequency_rank - b.frequency_rank
  })
}
