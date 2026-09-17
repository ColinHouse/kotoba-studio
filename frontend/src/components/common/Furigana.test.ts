import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import Furigana from './Furigana.vue'

describe('Furigana', () => {
  it('sets the reading above the kanji core only', () => {
    const wrapper = mount(Furigana, { props: { word: '奢る', reading: 'おごる' } })
    const ruby = wrapper.findAll('ruby')
    expect(ruby).toHaveLength(1)
    expect(ruby[0]!.find('rt').text()).toBe('おご')
    // base, annotation, okurigana — in that order, okurigana outside the ruby
    expect(wrapper.text()).toBe('奢おごる')
  })

  it('keeps the okurigana and leading kana outside the ruby', () => {
    const wrapper = mount(Furigana, { props: { word: 'お願い', reading: 'おねがい' } })
    expect(wrapper.findAll('ruby')).toHaveLength(1)
    expect(wrapper.find('rt').text()).toBe('ねが')
    expect(wrapper.text()).toBe('お願ねがい')
  })

  it('leaves kana-only words and missing readings unannotated', () => {
    const kana = mount(Furigana, { props: { word: 'おごる', reading: 'おごる' } })
    expect(kana.findAll('ruby')).toHaveLength(0)
    const blank = mount(Furigana, { props: { word: '奢る', reading: '' } })
    expect(blank.findAll('ruby')).toHaveLength(0)
    expect(blank.text()).toBe('奢る')
  })

  it('shows the bare word when show is off', () => {
    const wrapper = mount(Furigana, {
      props: { word: '奢る', reading: 'おごる', show: false },
    })
    expect(wrapper.findAll('ruby')).toHaveLength(0)
    expect(wrapper.text()).toBe('奢る')
  })
})
