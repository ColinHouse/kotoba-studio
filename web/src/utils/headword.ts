import type { DictEntry } from '@/api/types'
import { hasKanji } from './kana'

/** Headword form to learn: follow the script that actually appeared in the text. */
export function headwordFor(entry: DictEntry | undefined, surface: string, fallback: string): string {
  if (!entry) return fallback
  if (hasKanji(surface)) return entry.kanji[0] ?? entry.kana[0] ?? fallback
  if (entry.usually_kana || !entry.kanji.length) return entry.kana[0] ?? fallback
  return entry.kanji[0] ?? fallback
}
