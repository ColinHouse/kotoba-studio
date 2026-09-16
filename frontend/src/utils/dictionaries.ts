/** 释义来源：不猜语言，只如实标出它来自哪部词典。 */

export function senseOrigin(
  entry: { dict_title: string; dict_kind: string } | null,
  hasZh: boolean,
): string {
  if (hasZh) return 'user'
  if (!entry) return 'jmdict'
  // Sense.origin is a short column; keep the full title only when it fits.
  return entry.dict_title.length <= 16 ? entry.dict_title : entry.dict_kind
}

export function originLabel(origin: string): string {
  if (origin === 'jmdict') return 'JMdict'
  if (origin === 'user') return '自填'
  if (origin === 'yomitan') return 'Yomitan 词典'
  return origin
}
