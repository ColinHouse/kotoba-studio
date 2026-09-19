import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { setLocale } from '@/i18n'
import TextSourceGuide from './TextSourceGuide.vue'

function mountGuide(preferred: 'hook' | 'ocr') {
  return mount(TextSourceGuide, { props: { preferred } })
}

function sources(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('[data-source]').map((el) => el.attributes('data-source'))
}

describe('TextSourceGuide', () => {
  beforeEach(() => setLocale('zh-CN'))

  it('puts the recommended source first', () => {
    expect(sources(mountGuide('hook'))).toEqual(['hook', 'ocr'])
    expect(sources(mountGuide('ocr'))).toEqual(['ocr', 'hook'])
  })

  it('marks the preferred source and offers the other one a switch', async () => {
    const wrapper = mountGuide('hook')

    expect(wrapper.find('[data-source="hook"]').text()).toContain('推荐')
    expect(wrapper.find('[data-source="hook"]').find('button').exists()).toBe(false)

    const other = wrapper.find('[data-source="ocr"]')
    expect(other.find('button').text()).toBe('设为首选')
    await other.find('button').trigger('click')
    expect(wrapper.emitted('select')).toEqual([['ocr']])
  })

  it('keeps both routes reachable whatever the order', () => {
    for (const preferred of ['hook', 'ocr'] as const) {
      const wrapper = mountGuide(preferred)
      expect(sources(wrapper)).toHaveLength(2)
      expect(wrapper.find('[data-source="hook"] a').attributes('href')).toBe('#hook-status')
      expect(wrapper.find('[data-source="ocr"] a').attributes('href')).toBe('#ocr-collect')
      // Nothing is hidden or disabled by the preference.
      expect(wrapper.findAll('[data-source]').every((el) => !el.attributes('disabled'))).toBe(true)
    }
  })

  it('writes down the reason for each route, in one line', () => {
    const text = mountGuide('hook').text()
    expect(text).toContain('内存')
    expect(text).toContain('看得见')
  })
})
