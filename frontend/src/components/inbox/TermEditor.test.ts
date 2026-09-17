import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import type { DictEntry } from '@/api/types'
import TermEditor, { type ConfirmPayload } from './TermEditor.vue'
import type { PickedTerm } from './TokenChips.vue'

const ENTRY: DictEntry = {
  id: '1234567',
  dict_id: 1,
  dict_title: 'JMdict',
  dict_kind: 'jmdict',
  kanji: ['奢る'],
  kana: ['おごる'],
  senses: [
    {
      pos: ['v5r'],
      gloss_en: ['to treat', 'to liven up'],
      misc: [],
      field: [],
      info: [],
    },
  ],
  pos: ['v5r'],
  common: true,
  is_expression: false,
  usually_kana: false,
  headword: '奢る',
  reading: 'おごる',
}

function picked(overrides: Partial<PickedTerm> = {}): PickedTerm {
  return {
    headword: '奢る',
    reading: 'おごる',
    surface: '奢って',
    span_start: 5,
    span_end: 7,
    candidates: [ENTRY],
    term_id: null,
    known_status: null,
    pos: '動詞',
    is_expression: false,
    ...overrides,
  }
}

function confirmed(wrapper: ReturnType<typeof mount>): ConfirmPayload {
  const events = wrapper.emitted('confirm')
  expect(events).toBeTruthy()
  return events![0]![0] as ConfirmPayload
}

describe('TermEditor', () => {
  it('offers reading + cloze cards for a word with kanji, and emits them on confirm', async () => {
    const wrapper = mount(TermEditor, { props: { picked: picked(), busy: false } })
    expect(wrapper.text()).toContain('奢って')
    expect(wrapper.text()).toContain('词典候选')

    await wrapper.find('#term-gloss-zh').setValue('请客')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === '确认并建卡')!
      .trigger('click')

    const payload = confirmed(wrapper)
    expect(payload.headword).toBe('奢る')
    expect(payload.reading).toBe('おごる')
    expect(payload.surface).toBe('奢って')
    expect(payload.span_start).toBe(5)
    expect(payload.card_types).toEqual(['reading', 'cloze'])
    expect(payload.sense?.gloss_zh).toBe('请客')
    expect(payload.jmdict_id).toBe(ENTRY.id)
  })

  it('offers meaning cards instead for a kana-only word', async () => {
    const wrapper = mount(TermEditor, {
      props: {
        picked: picked({
          headword: 'おごる',
          surface: 'おごる',
          candidates: [{ ...ENTRY, kanji: [], headword: 'おごる' }],
        }),
        busy: false,
      },
    })
    await wrapper
      .findAll('button')
      .find((b) => b.text() === '确认并建卡')!
      .trigger('click')
    expect(confirmed(wrapper).card_types).toEqual(['meaning', 'cloze'])
  })

  it('reflects toggled card types in the payload', async () => {
    const wrapper = mount(TermEditor, { props: { picked: picked(), busy: false } })
    await wrapper
      .findAll('button')
      .find((b) => b.text() === '释义')!
      .trigger('click')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === '读音')!
      .trigger('click')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === '确认并建卡')!
      .trigger('click')
    expect(confirmed(wrapper).card_types).toEqual(['cloze', 'meaning'])
  })

  it('confirms with the keyboard and cancels with Escape', async () => {
    const wrapper = mount(TermEditor, { props: { picked: picked(), busy: false } })
    const section = wrapper.find('section')
    await section.trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('cancel')).toHaveLength(1)
    await section.trigger('keydown', { key: 'Enter', ctrlKey: true })
    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('will not confirm an empty headword', async () => {
    const wrapper = mount(TermEditor, { props: { picked: picked(), busy: false } })
    await wrapper.find('#term-headword').setValue('   ')
    const button = wrapper.findAll('button').find((b) => b.text() === '确认并建卡')!
    expect(button.attributes('disabled')).toBeDefined()
    await sectionKey(wrapper, { key: 'Enter', ctrlKey: true })
    expect(wrapper.emitted('confirm')).toBeUndefined()
  })
})

async function sectionKey(wrapper: ReturnType<typeof mount>, event: Record<string, unknown>) {
  await wrapper.find('section').trigger('keydown', event)
}
