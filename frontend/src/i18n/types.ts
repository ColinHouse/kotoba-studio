import type { ErrorCode } from './errors'

/** Every string the UI can show, grouped by where it comes from. */
export interface Messages {
  nav: {
    home: string
    capture: string
    inbox: string
    review: string
    stats: string
    library: string
    kanji: string
    sources: string
    settings: string
  }
  shell: {
    tagline: string
    activeSession: string
    noSource: string
    lines: string
    offline: string
  }
  settings: {
    language: {
      title: string
      zh: string
      en: string
    }
  }
  /** 中文留空：`translateError` 回退到后端原文，中文用户看到的字一个不变。 */
  errors: Partial<Record<ErrorCode, string>>
}
