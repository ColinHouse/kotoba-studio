import { describe, expect, it } from 'vitest'
import { ERROR_CODES } from './errors'
import { en } from './en'
import { locale, setLocale, t, translateError } from './index'

describe('i18n', () => {
  it('defaults to zh-CN, without guessing from the browser', () => {
    expect(locale.value).toBe('zh-CN')
    expect(t('nav.home')).toBe('首页')
  })

  it('switches languages', () => {
    setLocale('en')
    expect(t('nav.home')).toBe('Home')
    expect(t('settings.language.en')).toBe('English')
    setLocale('zh-CN')
    expect(t('nav.home')).toBe('首页')
  })

  it('has an English sentence for every backend error code', () => {
    for (const code of ERROR_CODES) {
      expect(en.errors[code]).toBeTruthy()
    }
  })

  it('keeps every Chinese error exactly as the backend wrote it', () => {
    for (const code of ERROR_CODES) {
      expect(translateError(code, '后端原文')).toBe('后端原文')
    }
  })

  it('maps English errors by stable code and falls back when the code is new', () => {
    setLocale('en')
    expect(translateError('bad_import', '后端原文')).toMatch(/import/i)
    expect(translateError('a_code_from_the_future', '后端原文')).toBe('后端原文')
    setLocale('zh-CN')
  })
})
