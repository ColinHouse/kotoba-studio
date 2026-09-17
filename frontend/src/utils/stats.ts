export interface Padding {
  top: number
  right: number
  bottom: number
  left: number
}

export interface BarRect {
  x: number
  y: number
  width: number
  height: number
  value: number
}

/**
 * Compute x, y, width, height for SVG bar charts.
 */
export function computeBarLayout(
  values: number[],
  chartWidth: number,
  chartHeight: number,
  padding: Padding = { top: 10, right: 10, bottom: 20, left: 10 },
  minMax: number = 5,
): BarRect[] {
  if (values.length === 0) return []

  const innerWidth = Math.max(0, chartWidth - padding.left - padding.right)
  const innerHeight = Math.max(0, chartHeight - padding.top - padding.bottom)
  const maxVal = Math.max(...values, minMax)

  const slotWidth = innerWidth / values.length
  const barWidth = Math.max(1, slotWidth * 0.7)
  const gap = (slotWidth - barWidth) / 2

  return values.map((val, i) => {
    const clampedVal = Math.max(0, val)
    const barH = maxVal > 0 ? (clampedVal / maxVal) * innerHeight : 0
    const x = padding.left + i * slotWidth + gap
    const y = padding.top + (innerHeight - barH)
    return {
      x: Number(x.toFixed(2)),
      y: Number(y.toFixed(2)),
      width: Number(barWidth.toFixed(2)),
      height: Number(barH.toFixed(2)),
      value: val,
    }
  })
}

/**
 * Compute rolling accuracy over a given window of days.
 * If total reviews in the rolling window is 0, returns null.
 */
export function computeRollingAccuracy(
  daily: { count: number; correct: number }[],
  windowSize: number = 7,
): (number | null)[] {
  if (daily.length === 0) return []

  return daily.map((_, idx) => {
    const start = Math.max(0, idx - windowSize + 1)
    const slice = daily.slice(start, idx + 1)
    const totalCount = slice.reduce((acc, d) => acc + d.count, 0)
    const totalCorrect = slice.reduce((acc, d) => acc + d.correct, 0)
    if (totalCount === 0) return null
    return Number((totalCorrect / totalCount).toFixed(4))
  })
}

/**
 * Generate SVG polyline points string from array of values (0.0 to 1.0).
 * Values of null are skipped.
 */
export function computePolylinePoints(
  values: (number | null)[],
  chartWidth: number,
  chartHeight: number,
  padding: Padding = { top: 10, right: 10, bottom: 20, left: 10 },
  minVal: number = 0,
  maxVal: number = 1,
): string {
  if (values.length === 0) return ''

  const innerWidth = Math.max(0, chartWidth - padding.left - padding.right)
  const innerHeight = Math.max(0, chartHeight - padding.top - padding.bottom)
  const range = maxVal - minVal || 1
  const step = values.length > 1 ? innerWidth / (values.length - 1) : innerWidth

  const pts: string[] = []
  values.forEach((v, i) => {
    if (v === null || Number.isNaN(v)) return
    const clamped = Math.max(minVal, Math.min(maxVal, v))
    const x = padding.left + i * step
    const y = padding.top + (1 - (clamped - minVal) / range) * innerHeight
    pts.push(`${x.toFixed(1)},${y.toFixed(1)}`)
  })

  return pts.join(' ')
}

/**
 * Format retention or ratio as a readable percentage string.
 */
export function formatPercent(val: number | null | undefined): string {
  if (val === null || val === undefined || Number.isNaN(val)) return '—'
  return `${(val * 100).toFixed(1)}%`
}
