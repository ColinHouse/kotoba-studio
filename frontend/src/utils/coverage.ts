/** 覆盖率展示：百分比与墨色深浅，阈值只在这里定义。 */

export function coveragePercent(value: number): string {
  return `${Math.round(value * 100)}%`
}

/** More known words means darker ink; the shade encodes the state, not a colour. */
export function coverageInk(value: number): string {
  if (value >= 0.85) return 'text-ink'
  if (value >= 0.6) return 'text-ink-70'
  if (value > 0) return 'text-ink-50'
  return 'text-ink-35'
}
