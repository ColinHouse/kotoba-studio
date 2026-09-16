/** 释义来源：不猜语言，只如实标出它来自哪部词典。 */

export interface DictionaryInfo {
  title: string
  kind: string
  entry_count: number
  revision: string | null
  attribution: string | null
}

export function dictionaryKindLabel(kind: string): string {
  if (kind === 'jmdict') return 'JMdict'
  if (kind === 'yomitan-freq') return '频率表'
  if (kind === 'yomitan') return 'Yomitan 词典'
  return kind
}

export function dictionaryCountLabel(dictionary: DictionaryInfo): string {
  const unit = dictionary.kind === 'yomitan-freq' ? '条频率' : '条词条'
  return `${dictionary.entry_count.toLocaleString()} ${unit}`
}

/** The list follows what is imported; JMdict's own `installed` flag stays separate. */
export function dictionaryListShows(dictionaries: DictionaryInfo[] | null | undefined): boolean {
  return !!dictionaries?.length
}

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
