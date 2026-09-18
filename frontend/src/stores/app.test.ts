import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ApiError } from '@/api/client'
import { setLocale } from '@/i18n'
import { useAppStore } from './app'

describe('app.fail', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    setLocale('zh-CN')
  })

  it('shows the backend message verbatim in Chinese (#130, decision two)', () => {
    const app = useAppStore()
    app.fail(new ApiError('bad_import', '这个文件读不了'))
    expect(app.toasts.at(-1)?.text).toBe('这个文件读不了')
  })

  it('maps the code to English for an English interface', () => {
    const app = useAppStore()
    setLocale('en')
    app.fail(new ApiError('bad_import', '这个文件读不了'))
    expect(app.toasts.at(-1)?.text).toMatch(/import/i)
  })

  it('keeps the local fallback for non-API errors', () => {
    const app = useAppStore()
    app.fail(new Error('boom'), '操作失败')
    expect(app.toasts.at(-1)?.text).toBe('操作失败')
  })
})
