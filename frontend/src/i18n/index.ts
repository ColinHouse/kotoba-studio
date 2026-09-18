import { ref } from 'vue'
import { en } from './en'
import { zhCN } from './zh-CN'
import type { Messages } from './types'

/**
 * Two locales, static strings, no plurals or date formatting: a typed
 * composable is enough, and it keeps the dependency list (and the lockfile,
 * which currently needs hand-merging) out of the picture. `vue-i18n` would buy
 * lazy loading and interpolation; nothing here needs either yet.
 *
 * Default is zh-CN and nothing is guessed from the browser: existing users must
 * not wake up to a different interface. The preference is a per-machine choice
 * in localStorage, not database state.
 */
export type Locale = 'zh-CN' | 'en'

const STORAGE_KEY = 'kotoba.language'
const messages: Record<Locale, Messages> = { 'zh-CN': zhCN, en }

type DotPaths<T> = {
  [K in keyof T & string]: T[K] extends Record<string, unknown> ? `${K}.${DotPaths<T[K]>}` : K
}[keyof T & string]

/** Every valid key, checked by vue-tsc: typos cannot reach the templates. */
export type MessagePath = DotPaths<Messages>

function readLocale(): Locale {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'zh-CN'
  } catch {
    return 'zh-CN' // private mode: the default, for this visit
  }
}

export const locale = ref<Locale>(readLocale())

export function setLocale(next: Locale): void {
  locale.value = next
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    /* the in-memory choice still applies for this visit */
  }
}

function lookup(source: Messages, path: string): string | undefined {
  const value = path
    .split('.')
    .reduce<unknown>((node, step) => (node as Record<string, unknown> | undefined)?.[step], source)
  return typeof value === 'string' ? value : undefined
}

/** Translate one key; a missing translation falls back to the zh-CN baseline. */
export function t(key: MessagePath): string {
  return lookup(messages[locale.value], key) ?? lookup(zhCN, key) ?? key
}

/**
 * The Chinese baseline for errors is the backend's own message, verbatim
 * (rule two of #130): `zh-CN` has an empty errors table on purpose. English
 * maps by the stable `code`; a code without an entry also falls back, because
 * the backend's Chinese beats a naked identifier.
 */
export function translateError(code: string, fallback: string): string {
  const table = messages[locale.value] as unknown as { errors: Record<string, string | undefined> }
  return table.errors[code] ?? fallback
}
