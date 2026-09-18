import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SetupChecklist from './SetupChecklist.vue'

const PROGRESS = {
  dict: true,
  region: false,
  lines: false,
  allDone: false,
  established: false,
}

function mountWith(overrides: Partial<typeof PROGRESS> = {}) {
  return mount(SetupChecklist, {
    props: { progress: { ...PROGRESS, ...overrides } },
    global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
  })
}

describe('SetupChecklist', () => {
  it('lists the three preparation steps with their state', () => {
    const wrapper = mountWith()
    const text = wrapper.text()
    expect(text).toContain('安装 JMdict 词典')
    expect(text).toContain('框一个采集区域')
    expect(text).toContain('接一个台词来源')
    expect(text).toContain('已完成') // the dictionary
    expect(wrapper.findAll('li')).toHaveLength(3)
  })

  it('links only the steps that are still outstanding', () => {
    const wrapper = mountWith()
    const links = wrapper.findAll('a')
    expect(links).toHaveLength(2) // region + lines, not the dictionary
    expect(links[0]!.text()).toContain('去处理')
  })

  it('offers no links and no work once everything is done', () => {
    const wrapper = mountWith({ dict: true, region: true, lines: true, allDone: true })
    expect(wrapper.findAll('a')).toHaveLength(0)
    expect(wrapper.findAll('.tag').map((tag) => tag.text())).toEqual(['已完成', '已完成', '已完成'])
  })

  it('can be dismissed for good', async () => {
    const wrapper = mountWith()
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('dismiss')).toHaveLength(1)
  })
})
