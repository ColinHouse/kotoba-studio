import type { ReaderBlock } from '@/api/types'

export type PageTurn = 'next' | 'prev' | null

/** 一次滑动至少要移动这么多像素，且明显偏水平，才算翻页。 */
export const SWIPE_MIN = 48

/** 键盘翻页：日漫从右往左，"往左的键"是往后读。 */
export function arrowTurn(rtl: boolean, key: string): PageTurn {
  if (key === 'ArrowLeft') return rtl ? 'next' : 'prev'
  if (key === 'ArrowRight') return rtl ? 'prev' : 'next'
  return null
}

/** 滑动翻页：dx 是手指在屏幕上的水平位移，向右为正。 */
export function swipeTurn(rtl: boolean, dx: number, dy = 0): PageTurn {
  if (Math.abs(dx) < SWIPE_MIN || Math.abs(dx) < Math.abs(dy) * 1.5) return null
  if (dx > 0) return rtl ? 'next' : 'prev'
  return rtl ? 'prev' : 'next'
}

export interface NaturalSize {
  width: number
  height: number
}

/** 把页面像素坐标的框换算成图片上的百分比，缩放与居中都不影响它。 */
export function boxStyle(box: [number, number, number, number], image: NaturalSize) {
  if (image.width <= 0 || image.height <= 0) return {}
  return {
    left: `${(box[0] / image.width) * 100}%`,
    top: `${(box[1] / image.height) * 100}%`,
    width: `${((box[2] - box[0]) / image.width) * 100}%`,
    height: `${((box[3] - box[1]) / image.height) * 100}%`,
  }
}

/** 已建过卡的文字框用更深的墨；颜色只留给"当前"。 */
export function boxInk(block: Pick<ReaderBlock, 'card_count'>): string {
  return block.card_count > 0 ? 'reader-box reader-box-carded' : 'reader-box'
}

/** 文本回退里的行：同样按"有没有卡"分墨色。 */
export function lineInk(block: Pick<ReaderBlock, 'card_count'>): string {
  return block.card_count > 0 ? 'reader-line reader-line-carded' : 'reader-line'
}

/** 输入框里按方向键是移动光标，不是翻页。 */
export function isTypingTarget(
  target: { tagName?: string; isContentEditable?: boolean } | null,
): boolean {
  if (target?.isContentEditable) return true
  const tag = target?.tagName?.toLowerCase()
  return tag === 'input' || tag === 'textarea' || tag === 'select'
}
