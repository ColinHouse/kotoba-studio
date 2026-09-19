import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import type { HookStatus } from '@/api/types'
import HookStatusPanel from './HookStatus.vue'

const { listHooks, connectHook, disconnectHook, probeHook } = vi.hoisted(() => ({
  listHooks: vi.fn(),
  connectHook: vi.fn(),
  disconnectHook: vi.fn(),
  probeHook: vi.fn(),
}))

vi.mock('@/api/capture', () => ({ listHooks, connectHook, disconnectHook, probeHook }))

function hook(overrides: Partial<HookStatus> = {}): HookStatus {
  return {
    name: 'textractor',
    url: 'ws://127.0.0.1:6677',
    connected: false,
    status: 'idle',
    last_text: null,
    last_text_at: null,
    error: null,
    ...overrides,
  }
}

const PRESETS = [
  hook(),
  hook({ name: 'agent', url: 'ws://127.0.0.1:9001' }),
  hook({ name: 'luna', url: 'ws://127.0.0.1:2333' }),
]

async function mountPanel() {
  const wrapper = mount(HookStatusPanel)
  await flushPromises()
  return wrapper
}

function button(wrapper: ReturnType<typeof mount>, label: string) {
  return wrapper.findAll('button').find((b) => b.text() === label)!
}

describe('HookStatus', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    listHooks.mockResolvedValue(PRESETS)
  })

  it('shows the not-detected state and how to fix it, without the ws URL', async () => {
    const wrapper = await mountPanel()

    expect(wrapper.text()).toContain('未检测到')
    expect(wrapper.text()).toContain('WebSocket 扩展')
    expect(wrapper.find('a').attributes('href')).toContain('textractor')
    expect(wrapper.text()).not.toContain('ws://')

    wrapper.unmount()
  })

  it('shows the last line and how fresh it is once connected', async () => {
    listHooks.mockResolvedValue([
      hook({
        connected: true,
        status: 'connected',
        last_text: 'それでも、私は',
        last_text_at: new Date(Date.now() - 5000).toISOString(),
      }),
      ...PRESETS.slice(1),
    ])
    const wrapper = await mountPanel()

    expect(wrapper.text()).toContain('已连接')
    expect(wrapper.text()).toContain('それでも、私は')
    expect(wrapper.text()).toContain('秒前')
    expect(button(wrapper, '断开')).toBeTruthy()

    wrapper.unmount()
  })

  it('distinguishes retrying from not detected', async () => {
    listHooks.mockResolvedValue([
      hook({ status: 'connecting', error: 'OSError: connection refused' }),
      ...PRESETS.slice(1),
    ])
    const wrapper = await mountPanel()

    expect(wrapper.text()).toContain('正在连接')
    expect(wrapper.text()).toContain('WebSocket 扩展')

    wrapper.unmount()
  })

  it('connects to the shown tool only when asked', async () => {
    connectHook.mockResolvedValue(hook())
    const wrapper = await mountPanel()

    await button(wrapper, '连接').trigger('click')
    await flushPromises()

    expect(connectHook).toHaveBeenCalledWith('textractor', undefined)
    wrapper.unmount()
  })

  it('keeps the address behind the advanced fold and can save a new port', async () => {
    connectHook.mockResolvedValue(hook())
    const wrapper = await mountPanel()

    expect(wrapper.find('#hook-url-textractor').exists()).toBe(false)
    await button(wrapper, '高级').trigger('click')

    const input = wrapper.find('#hook-url-textractor')
    expect((input.element as HTMLInputElement).value).toBe('ws://127.0.0.1:6677')
    await input.setValue('ws://127.0.0.1:7777')
    await button(wrapper, '保存并连接').trigger('click')
    await flushPromises()

    expect(connectHook).toHaveBeenCalledWith('textractor', 'ws://127.0.0.1:7777')
    wrapper.unmount()
  })

  it('does not keep a connection the probe could not prove', async () => {
    probeHook.mockResolvedValue({ ok: false, error: 'OSError: connection refused' })
    const wrapper = await mountPanel()

    await button(wrapper, '测试连接').trigger('click')
    await flushPromises()

    expect(probeHook).toHaveBeenCalledWith('textractor')
    expect(connectHook).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('starts the retrying client after a successful probe', async () => {
    probeHook.mockResolvedValue({ ok: true, error: null })
    connectHook.mockResolvedValue(hook({ connected: true, status: 'connected' }))
    const wrapper = await mountPanel()

    await button(wrapper, '测试连接').trigger('click')
    await flushPromises()

    expect(connectHook).toHaveBeenCalledWith('textractor')
    wrapper.unmount()
  })
})
