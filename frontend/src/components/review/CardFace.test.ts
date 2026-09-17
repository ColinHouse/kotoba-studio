import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import type { CardFace as CardFaceData } from '@/api/types'
import CardFace from './CardFace.vue'

const READING = 'おごる'
const GLOSS = '奢侈；请客'
const SENTENCE = '今日は私が奢るよ'
const SCREENSHOT = 'screens/20260101/abc.png'
const AUDIO = 'audio/20260101/abc.opus'

function face(overrides: Partial<CardFaceData> = {}): CardFaceData {
  return {
    id: 1,
    term_id: 1,
    card_type: 'reading',
    primary_encounter_id: 1,
    review_owner: 'desktop',
    suspended: false,
    state: 1,
    step: null,
    stability: null,
    difficulty: null,
    due: null,
    last_review: null,
    created_at: '2026-09-01T00:00:00Z',
    headword: '奢る',
    reading: READING,
    term: {
      id: 1,
      headword: '奢る',
      reading: READING,
      pos: '動詞',
      jmdict_id: null,
      known_status: 'learning',
      note: null,
      created_at: '2026-09-01T00:00:00Z',
      senses: [{ id: 1, gloss_zh: GLOSS, gloss_en: 'to treat', origin: 'jmdict', ord: 0 }],
      encounter_count: 1,
      source_count: 1,
      card_count: 1,
      frequency_rank: null,
      trap: null,
    },
    encounter: {
      id: 1,
      line_id: 1,
      term_id: 1,
      sense_id: 1,
      surface: '奢る',
      span_start: 5,
      span_end: 7,
      contraction_of: null,
      ai_explanation: null,
      created_at: '2026-09-01T00:00:00Z',
      line_text: SENTENCE,
      screenshot_path: SCREENSHOT,
      audio_path: AUDIO,
      captured_at: '2026-09-01T00:00:00Z',
      source_id: 1,
      source_title: '某作',
    },
    other_encounters: 0,
    cloze_text: '今日は私が＿＿よ',
    pitches: [],
    preview: { again: '', hard: '', good: '', easy: '' },
    ...overrides,
  }
}

describe('CardFace', () => {
  it('never leaks the answer on the front (invariant §5.2)', () => {
    const wrapper = mount(CardFace, { props: { face: face(), revealed: false } })
    const text = wrapper.text()

    expect(text).toContain('奢る') // the prompt itself is there
    expect(text).not.toContain(READING) // the reading is the answer
    expect(text).not.toContain(GLOSS) // the gloss is the answer
    expect(text).not.toContain('今日は私が') // not even a sentence fragment
    expect(wrapper.html()).not.toContain(SCREENSHOT) // a screenshot gives it away
    expect(wrapper.html()).not.toContain(AUDIO) // and so does the original voice
  })

  it('shows the given reading on a meaning card but still hides the gloss', () => {
    const wrapper = mount(CardFace, {
      props: { face: face({ card_type: 'meaning' }), revealed: false },
    })
    const text = wrapper.text()
    expect(text).toContain(READING) // meaning cards give the reading as a hint
    expect(text).not.toContain(GLOSS)
    expect(text).not.toContain(SENTENCE)
  })

  it('shows the cloze text with the blank, never the full sentence', () => {
    const wrapper = mount(CardFace, {
      props: { face: face({ card_type: 'cloze' }), revealed: false },
    })
    expect(wrapper.text()).toContain('＿＿')
    expect(wrapper.text()).not.toContain(SENTENCE)
  })

  it('reveals reading, gloss, sentence and screenshot on the back', () => {
    const wrapper = mount(CardFace, { props: { face: face(), revealed: true } })
    const text = wrapper.text()
    expect(text).toContain('奢おごる') // the headword with its reading set above
    expect(text).toContain(GLOSS)
    expect(text).toContain('今日は私が奢おごるよ') // the whole original line
    expect(wrapper.html()).toContain(SCREENSHOT)
    expect(wrapper.html()).toContain(AUDIO)
  })
})
