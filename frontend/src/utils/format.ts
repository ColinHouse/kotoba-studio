export function humanInterval(iso: string, from: Date = new Date()): string {
  const ms = new Date(iso).getTime() - from.getTime()
  const min = Math.round(ms / 60000)
  if (min < 1) return '<1分钟'
  if (min < 60) return `${min}分钟`
  const hours = Math.round(min / 60)
  if (hours < 24) return `${hours}小时`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days}天`
  const months = Math.round(days / 30)
  if (months < 12) return `${months}个月`
  return `${(days / 365).toFixed(1)}年`
}

export function relTime(iso: string, now: Date = new Date()): string {
  const diff = now.getTime() - new Date(iso).getTime()
  const min = Math.round(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const h = Math.round(min / 60)
  if (h < 24) return `${h} 小时前`
  const d = Math.round(h / 24)
  if (d < 7) return `${d} 天前`
  return new Date(iso).toLocaleDateString('zh-CN')
}

/** Seconds-first relative time for a live feed, where "刚刚" is not proof of life. */
export function relSeconds(iso: string, now: Date = new Date()): string {
  const s = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 1000))
  if (s < 60) return `${s} 秒前`
  const m = Math.round(s / 60)
  if (m < 60) return `${m} 分钟前`
  const h = Math.round(m / 60)
  if (h < 24) return `${h} 小时前`
  return `${Math.round(h / 24)} 天前`
}

export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

export function fmtDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h) return `${h} 小时 ${m} 分`
  return m ? `${m} 分 ${s} 秒` : `${s} 秒`
}

export function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

export const CARD_TYPE_LABEL: Record<string, string> = {
  reading: '读音',
  meaning: '释义',
  cloze: '填空',
  listening: '听音',
}

export const STATUS_LABEL: Record<string, string> = {
  unknown: '未学',
  learning: '学习中',
  known: '已掌握',
  ignored: '忽略',
}

export const KIND_LABEL: Record<string, string> = {
  game: 'Galgame',
  anime: '动画',
  video: '视频',
  manga: '漫画',
  other: '其他',
}
