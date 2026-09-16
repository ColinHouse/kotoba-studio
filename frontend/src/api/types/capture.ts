/** 采集：作品、会话、句子、截屏与 OCR。Capture-side payloads. */

export type Kind = 'game' | 'anime' | 'video' | 'manga' | 'other'

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

export interface OcrBlock { text: string; confidence: number; box: [number, number, number, number] }

export interface OcrResult { text: string; blocks: OcrBlock[]; provider: string; elapsed_ms: number; normalized?: string }

export interface Provider { name: string; available: boolean; note: string; recommended: boolean }

export interface Display { index: number; left: number; top: number; width: number; height: number }

export interface Screenshot { path: string; width: number; height: number; scale: number; region: Region }

export interface CollectResult { ocr: OcrResult; screenshot_path: string | null; scale: number; line: Line | null; duplicate: boolean }
