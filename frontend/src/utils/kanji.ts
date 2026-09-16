/** 汉字掌握度的墨色深浅与标签：越熟练墨色越深，不新造颜色。 */

import type { KanjiStatus } from '@/api/types'

const INK: Record<KanjiStatus, string> = {
  unseen: 'text-ink-35',
  seen: 'text-ink-50',
  learning: 'text-ink-70',
  mastered: 'text-ink',
}

const LABEL: Record<KanjiStatus, string> = {
  unseen: '未见过',
  seen: '见过',
  learning: '学习中',
  mastered: '已掌握',
}

export function kanjiInk(status: KanjiStatus): string {
  return INK[status]
}

export function kanjiStatusLabel(status: KanjiStatus): string {
  return LABEL[status]
}
