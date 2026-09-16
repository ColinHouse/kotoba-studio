export type Kind = 'game' | 'anime' | 'video' | 'manga' | 'other'
export type KnownStatus = 'unknown' | 'learning' | 'known' | 'ignored'
export type CardType = 'reading' | 'meaning' | 'cloze' | 'listening'
export type Owner = 'desktop' | 'mobile' | 'any'

export interface Region { left: number; top: number; width: number; height: number; display: number }

export interface Source {
  id: number; title: string; title_ja: string | null; kind: Kind; region: Region | null
  created_at: string; line_count: number; term_count: number
}

export interface Session {
  id: number; source_id: number | null; source_title: string | null; mode: string; text_source: string
  started_at: string; ended_at: string | null; stats: Record<string, number> | null; line_count: number
}

export interface Line {
  id: number; session_id: number | null; source_id: number | null; text: string; raw_text: string | null
  origin: string; screenshot_path: string | null; audio_path: string | null; position: unknown
  speaker: string | null; translation_zh: string | null; status: 'inbox' | 'kept' | 'discarded'
  captured_at: string; encounter_count: number
}

export interface DictSense { pos: string[]; gloss_en: string[]; misc: string[]; field: string[]; info: string[] }
export interface DictEntry {
  id: string; dict_id: number; kanji: string[]; kana: string[]; senses: DictSense[]; pos: string[]
  common: boolean; is_expression: boolean; usually_kana: boolean; headword: string; reading: string
}

export interface Token {
  surface: string; lemma: string; base: string; reading: string; reading_base: string
  pos1: string; pos2: string; start: number; end: number; is_content: boolean
  candidates: DictEntry[]; term_id: number | null; known_status: KnownStatus | null; encountered: boolean
}
export interface Span {
  start_tok: number; end_tok: number; text: string; matched_form: string; reading: string
  candidates: DictEntry[]; term_id: number | null; known_status: KnownStatus | null
}
export interface Contraction { form: string; full: string; note_zh: string }
export interface Analysis { line_id: number; text: string; tokens: Token[]; spans: Span[]; contractions: Contraction[] }

export interface Sense { id: number; gloss_zh: string | null; gloss_en: string | null; origin: string; ord: number }
export interface Trap { headword: string; reading: string; zh_reading_meaning: string; ja_meaning: string; note: string }
export interface Term {
  id: number; headword: string; reading: string; pos: string | null; jmdict_id: string | null
  known_status: KnownStatus; note: string | null; created_at: string; senses: Sense[]
  encounter_count: number; source_count: number; card_count: number; trap: Trap | null
}
export interface Explanation {
  meaning_here?: string; form?: string | null; tone?: string; needs_context?: string | null
  daily_usable?: string; trap_for_zh?: string | null; confidence?: number; _model?: string; _created_at?: string
}
export interface Encounter {
  id: number; line_id: number; term_id: number; sense_id: number | null; surface: string
  span_start: number; span_end: number; contraction_of: string | null; ai_explanation: Explanation | null
  created_at: string; line_text: string; screenshot_path: string | null; audio_path: string | null
  captured_at: string; source_id: number | null; source_title: string | null
}
export interface TermDetail extends Term { encounters: Encounter[]; cards: Card[] }

export interface Card {
  id: number; term_id: number; card_type: CardType; primary_encounter_id: number | null
  review_owner: Owner; suspended: boolean; state: number; step: number | null; stability: number | null
  difficulty: number | null; due: string | null; last_review: string | null; created_at: string
  headword: string | null; reading: string | null
}
export interface CardFace extends Card {
  term: Term; encounter: Encounter | null; other_encounters: number; cloze_text: string | null
  preview: Record<'again' | 'hard' | 'good' | 'easy', string>
}

export interface Device { id: string; name: string; kind: 'desktop' | 'mobile'; created_at: string; last_seen: string }

export interface QuizItem {
  card_id: number; term_id: number; encounter_id: number; kind: CardType; prompt: string
  answer: string | null; accept: string[]; headword: string; reading: string; surface: string
  hint: string | null; audio_path: string | null
}
export interface SessionSummary {
  session_id: number; source_id: number | null; started_at: string; ended_at: string | null; duration_s: number
  lines_total: number; kept: number; inbox: number; discarded: number
  new_terms: { id: number; headword: string; reading: string }[]
  seen_again_terms: { id: number; headword: string; reading: string }[]
  cards_created: number; quiz: { answered: number; correct: number }
}

export interface OcrBlock { text: string; confidence: number; box: [number, number, number, number] }
export interface OcrResult { text: string; blocks: OcrBlock[]; provider: string; elapsed_ms: number; normalized?: string }
export interface Provider { name: string; available: boolean; note: string; recommended: boolean }
export interface Display { index: number; left: number; top: number; width: number; height: number }
export interface Screenshot { path: string; width: number; height: number; scale: number; region: Region }
export interface CollectResult { ocr: OcrResult; screenshot_path: string | null; scale: number; line: Line | null; duplicate: boolean }

export interface Settings {
  review_owner_default: Owner | null; desired_retention: number; ai_provider: string; ai_base_url: string
  ai_model: string; ocr_provider: string; active_session_id: number | null; ui_language: string
}
export interface ConnectInfo { urls: string[]; primary_url: string; qr_svg: string; port: number; host: string; lan_enabled: boolean; hint: string | null }
export interface DictStatus {
  installed: boolean
  dictionaries: { id: number; title: string; kind: string; revision: string | null; entry_count: number; imported_at: string }[]
  install: { state: string; message: string; done: number; total: number }
}
export interface Backup { name: string; size: number; created_at: string }
export interface CardStats { total: number; new: number; due_now: number; by_owner: Record<string, number>; by_state: Record<string, number> }
export interface AiUsage { calls: number; failed: number; prompt_tokens: number; completion_tokens: number; cost_estimate_usd: number; by_model: { model: string; calls: number; cost_estimate_usd: number }[] }
