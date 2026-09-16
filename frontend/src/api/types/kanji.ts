export type KanjiStatus = 'unseen' | 'seen' | 'learning' | 'mastered'

export interface KanjiEntry {
  character: string
  grade: number | null
  jlpt: number | null
  stroke_count: number | null
  frequency: number | null
  terms: number
  status: KanjiStatus
  scope: 'jouyou' | 'other'
}

export interface KanjiSummary {
  total: number
  unseen: number
  seen: number
  learning: number
  mastered: number
}

export interface KanjiGrid {
  installed: boolean
  summary: KanjiSummary
  kanji: KanjiEntry[]
}

export interface KanjiTerm {
  term_id: number
  headword: string
  reading: string
  known_status: string
  has_card: boolean
}

export interface KanjiTerms {
  character: string
  terms: KanjiTerm[]
}

export interface SourceKanji {
  character: string
  grade: number | null
  stroke_count: number | null
  occurrences: number
  terms: number
}
