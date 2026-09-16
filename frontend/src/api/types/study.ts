/** 学习：分析结果、词条、语境、卡片与短测。Study-side payloads. */

export type KnownStatus = 'unknown' | 'learning' | 'known' | 'ignored'

export type CardType = 'reading' | 'meaning' | 'cloze' | 'listening'

export type Owner = 'desktop' | 'mobile' | 'any'

export interface DictSense {
  pos: string[]
  gloss_en: string[]
  misc: string[]
  field: string[]
  info: string[]
}

export interface DictEntry {
  id: string
  dict_id: number
  kanji: string[]
  kana: string[]
  senses: DictSense[]
  pos: string[]
  common: boolean
  is_expression: boolean
  usually_kana: boolean
  headword: string
  reading: string
}

export interface Token {
  surface: string
  lemma: string
  base: string
  reading: string
  reading_base: string
  pos1: string
  pos2: string
  start: number
  end: number
  is_content: boolean
  candidates: DictEntry[]
  term_id: number | null
  known_status: KnownStatus | null
  encountered: boolean
  frequency_rank: number | null
}

export interface Span {
  start_tok: number
  end_tok: number
  text: string
  matched_form: string
  reading: string
  candidates: DictEntry[]
  term_id: number | null
  known_status: KnownStatus | null
}

export interface Contraction {
  form: string
  full: string
  note_zh: string
}

export interface Analysis {
  line_id: number
  text: string
  tokens: Token[]
  spans: Span[]
  contractions: Contraction[]
}

export interface Sense {
  id: number
  gloss_zh: string | null
  gloss_en: string | null
  origin: string
  ord: number
}

export interface Trap {
  headword: string
  reading: string
  zh_reading_meaning: string
  ja_meaning: string
  note: string
}

export interface Term {
  id: number
  headword: string
  reading: string
  pos: string | null
  jmdict_id: string | null
  known_status: KnownStatus
  note: string | null
  created_at: string
  senses: Sense[]
  encounter_count: number
  source_count: number
  card_count: number
  frequency_rank: number | null
  trap: Trap | null
}

export interface CoverageWord {
  term_id: number
  headword: string
  reading: string
  rank: number | null
  count: number
}

export interface Coverage {
  total_tokens: number
  distinct_terms: number
  known_tokens: number
  known_terms: number
  coverage: number
  distinct_coverage: number
  has_frequency: boolean
  unknown_top: CoverageWord[]
}

export interface Explanation {
  meaning_here?: string
  form?: string | null
  tone?: string
  needs_context?: string | null
  daily_usable?: string
  trap_for_zh?: string | null
  confidence?: number
  _model?: string
  _created_at?: string
}

export interface Encounter {
  id: number
  line_id: number
  term_id: number
  sense_id: number | null
  surface: string
  span_start: number
  span_end: number
  contraction_of: string | null
  ai_explanation: Explanation | null
  created_at: string
  line_text: string
  screenshot_path: string | null
  audio_path: string | null
  captured_at: string
  source_id: number | null
  source_title: string | null
}

export interface TermDetail extends Term {
  encounters: Encounter[]
  cards: Card[]
}

export interface Card {
  id: number
  term_id: number
  card_type: CardType
  primary_encounter_id: number | null
  review_owner: Owner
  suspended: boolean
  state: number
  step: number | null
  stability: number | null
  difficulty: number | null
  due: string | null
  last_review: string | null
  created_at: string
  headword: string | null
  reading: string | null
}

export interface CardPitch {
  reading: string
  accent: number
  pattern: string
  label: string
}

export interface CardFace extends Card {
  term: Term
  encounter: Encounter | null
  other_encounters: number
  cloze_text: string | null
  pitches: CardPitch[]
  preview: Record<'again' | 'hard' | 'good' | 'easy', string>
}

export type QuizKind = CardType | 'pitch'

export interface QuizItem {
  card_id: number
  term_id: number
  encounter_id: number
  kind: QuizKind
  prompt: string
  answer: string | null
  accept: string[]
  headword: string
  reading: string
  surface: string
  hint: string | null
  audio_path: string | null
  choices: string[]
}

export interface SessionSummary {
  session_id: number
  source_id: number | null
  started_at: string
  ended_at: string | null
  duration_s: number
  lines_total: number
  kept: number
  inbox: number
  discarded: number
  new_terms: { id: number; headword: string; reading: string }[]
  seen_again_terms: { id: number; headword: string; reading: string }[]
  cards_created: number
  quiz: { answered: number; correct: number }
}
