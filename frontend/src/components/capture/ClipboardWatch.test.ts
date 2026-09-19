import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { setLocale } from '@/i18n'
import ClipboardWatch from './ClipboardWatch.vue'

const { clipboardStatus, startClipboard, stopClipboard } = vi.hoisted(() => ({
  clipboardStatus: vi.fn(),
  startClipboard: vi.fn(),
  stopClipboard: vi.fn(),
}))

vi.mock('@/api/capture', () => ({ clipboardStatus, startClipboard, stopClipboard }))

async function mountWatch() {
  const wrapper = mount(ClipboardWatch)
  await flushPromises()
  return wrapper
}

describe('ClipboardWatch', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    setLocale('zh-CN')
    vi.clearAllMocks()
    clipboardStatus.mockResolvedValue({ running: false, captured: 0 })
  })

  it('starts off and can be switched on', async () => {
    startClipboard.mockResolvedValue({ running: true, captured: 3 })
    const wrapper = await mountWatch()

    expect(wrapper.text()).toContain('未开启')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(startClipboard).toHaveBeenCalled()
    expect(wrapper.text()).toContain('监听中')
    expect(wrapper.text()).toContain('3')
  })

  it('can be switched off and explains the extension-free route', async () => {
    clipboardStatus.mockResolvedValue({ running: true, captured: 12 })
    stopClipboard.mockResolvedValue({ running: false, captured: 12 })
    const wrapper = await mountWatch()

    expect(wrapper.text()).toContain('已收到')
    expect(wrapper.text()).toContain('Textractor')
    await wrapper.find('button').trigger('click')
    await flushPromises()

    expect(stopClipboard).toHaveBeenCalled()
    expect(wrapper.text()).toContain('未开启')
  })
})
