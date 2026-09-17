import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import type { CompareResult } from '@/api/types'
import EngineCompare from './EngineCompare.vue'

const RESULTS: CompareResult[] = [
  { provider: 'vision', text: 'こんにちは', ms: 900, error: null },
  { provider: 'winocr', text: '', ms: 40, error: '没有安装日语语言包' },
]

function rowFor(wrapper: ReturnType<typeof mount>, provider: string) {
  return wrapper.findAll('button').find((button) => button.text().includes(provider))!
}

describe('EngineCompare', () => {
  it('cannot select an engine that failed', async () => {
    const wrapper = mount(EngineCompare, {
      props: { results: RESULTS, current: 'vision', running: false, canRun: true },
    })
    expect(wrapper.text()).toContain('没有安装日语语言包')

    const failed = rowFor(wrapper, 'winocr')
    expect(failed.attributes('disabled')).toBeDefined()
    await failed.trigger('click')
    expect(wrapper.emitted('select')).toBeUndefined()
  })

  it('selects a working engine', async () => {
    const wrapper = mount(EngineCompare, {
      props: { results: RESULTS, current: 'auto', running: false, canRun: true },
    })
    await rowFor(wrapper, 'vision').trigger('click')
    expect(wrapper.emitted('select')).toEqual([['vision']])
  })

  it('will not run the comparison before a region is framed', async () => {
    const wrapper = mount(EngineCompare, {
      props: { results: [], current: 'auto', running: false, canRun: false },
    })
    const run = wrapper.findAll('button')[0]!
    expect(run.attributes('disabled')).toBeDefined()
    await run.trigger('click')
    expect(wrapper.emitted('run')).toBeUndefined()
    expect(wrapper.text()).toContain('先在左侧框选对话框区域')
  })
})
