import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { OcrResult } from '@/api/types'
import { setLocale } from '@/i18n'
import OcrResultView from './OcrResultView.vue'

const writeText = vi.fn()

function result(overrides: Partial<OcrResult> = {}): OcrResult {
  return {
    text: '今日は俺が奢ってやるよ。',
    blocks: [
      { text: '今日は', confidence: 0.975, box: [0.1, 0.2, 0.3, 0.1] },
      { text: '奢って', confidence: 0.42, box: [0.4, 0.3, 0.2, 0.1] },
    ],
    provider: 'winocr',
    elapsed_ms: 123,
    ...overrides,
  }
}

const IMAGE = { src: '/media/previews/20260101/a.png' }

describe('OcrResultView', () => {
  beforeEach(() => {
    setLocale('zh-CN')
    writeText.mockReset()
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
  })

  it('draws one box per block, positioned by the normalized coordinates', () => {
    const wrapper = mount(OcrResultView, { props: { result: result(), image: IMAGE } })
    const boxes = wrapper.findAll('[data-ocr-box]')

    expect(boxes).toHaveLength(2)
    expect(boxes[0]!.attributes('style')).toContain('left: 10%')
    expect(boxes[0]!.attributes('style')).toContain('top: 20%')
    expect(boxes[0]!.attributes('style')).toContain('width: 30%')
    expect(boxes[0]!.attributes('style')).toContain('height: 10%')
    expect(boxes[1]!.attributes('style')).toContain('left: 40%')
  })

  it('marks the block under 0.6 with a different line style, not a colour', () => {
    const wrapper = mount(OcrResultView, { props: { result: result(), image: IMAGE } })
    const boxes = wrapper.findAll('[data-ocr-box]')

    expect(boxes[0]!.classes()).not.toContain('ocr-box-low')
    expect(boxes[1]!.classes()).toContain('ocr-box-low')
  })

  it('shows the engine, how long it took and each confidence', () => {
    const wrapper = mount(OcrResultView, { props: { result: result(), image: IMAGE } })

    expect(wrapper.text()).toContain('winocr')
    expect(wrapper.text()).toContain('123 ms')
    expect(wrapper.text()).toContain('97.5%')
    expect(wrapper.text()).toContain('42.0%')
  })

  it('copies a block when it is clicked', async () => {
    writeText.mockResolvedValue(undefined)
    const wrapper = mount(OcrResultView, { props: { result: result(), image: IMAGE } })

    await wrapper.findAll('[data-ocr-box]')[1]!.trigger('click')
    await flushPromises()

    expect(writeText).toHaveBeenCalledWith('奢って')
    expect(wrapper.findAll('[data-ocr-box]')[1]!.text()).toContain('已复制')
  })

  it('crops the screenshot down to the region the blocks were read from', () => {
    const wrapper = mount(OcrResultView, {
      props: {
        result: result(),
        image: { src: '/p.png', crop: { x: 0.25, y: 0.5, width: 0.5, height: 0.25 } },
      },
    })

    const stage = wrapper.find('.ocr-stage')
    expect(stage.classes()).toContain('ocr-stage-crop')
    expect(stage.attributes('style')).toContain('aspect-ratio: 0.5 / 0.25')

    const img = wrapper.find('.ocr-image')
    expect(img.attributes('style')).toContain('width: 200%')
    expect(img.attributes('style')).toContain('left: -50%')
    expect(img.attributes('style')).toContain('top: -200%')
  })

  it('falls back to plain text when the engine returns no blocks', () => {
    const wrapper = mount(OcrResultView, {
      props: {
        result: result({ blocks: [], text: 'え、本当に？', normalized: 'え、本当に？' }),
        image: null,
      },
    })

    expect(wrapper.findAll('[data-ocr-box]')).toHaveLength(0)
    expect(wrapper.text()).toContain('え、本当に？')
    expect(wrapper.text()).toContain('不提供分块')
  })
})
