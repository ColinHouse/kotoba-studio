/** 采集：作品、会话、句子、截屏与 OCR。Capture-side payloads. */

export type Kind = 'game' | 'anime' | 'video' | 'manga' | 'other'

export interface Region {
  left: number
  top: number
  width: number
  height: number
  display: number
}

/** The game window a work is bound to; its box is relative to the client area. */
export interface WindowBinding {
  process: string
  title: string | null
  /** 客户区比例（0–1）；`unit` 缺失表示 #124 之前存的像素偏移，读取端两者都认。 */
  region: {
    unit?: 'ratio'
    left: number
    top: number
    width: number
    height: number
  } | null
}

/** One visible top-level window, as `GET /api/capture/windows` reports it. */
export interface GameWindow {
  handle: number
  title: string
  process: string
  pid: number
  left: number
  top: number
  width: number
  height: number
  client: [number, number, number, number]
  display: number
}

export interface Source {
  id: number
  title: string
  title_ja: string | null
  kind: Kind
  region: Region | null
  window: WindowBinding | null
  created_at: string
  line_count: number
  term_count: number
  known_term_count: number
}

export interface Session {
  id: number
  source_id: number | null
  source_title: string | null
  mode: string
  text_source: string
  started_at: string
  ended_at: string | null
  stats: Record<string, number> | null
  line_count: number
}

export interface Line {
  id: number
  session_id: number | null
  source_id: number | null
  text: string
  raw_text: string | null
  origin: string
  screenshot_path: string | null
  audio_path: string | null
  position: unknown
  locator: Record<string, unknown> | null
  ord: number | null
  speaker: string | null
  translation_zh: string | null
  status: 'inbox' | 'kept' | 'discarded'
  captured_at: string
  encounter_count: number
  unknown_count: number | null
}

export interface OcrBlock {
  text: string
  confidence: number
  box: [number, number, number, number]
}

export interface OcrResult {
  text: string
  blocks: OcrBlock[]
  provider: string
  elapsed_ms: number
  normalized?: string
}

export interface Provider {
  name: string
  available: boolean
  note: string
  recommended: boolean
}

/** The OS-clipboard watcher: a zero-install transport for hook tools. */
export interface ClipboardStatus {
  running: boolean
  captured: number
}

export interface CompareResult {
  provider: string
  text: string
  ms: number
  error: string | null
}

export interface Display {
  index: number
  left: number
  top: number
  width: number
  height: number
}

export interface Screenshot {
  path: string
  width: number
  height: number
  scale: number
  region: Region
}

export interface CollectResult {
  ocr: OcrResult
  screenshot_path: string | null
  scale: number
  line: Line | null
  duplicate: boolean
}

/** One outbound hook tool, as `GET /api/capture/hooks` reports it. */
export type HookState = 'idle' | 'connecting' | 'connected'

export interface HookStatus {
  name: string
  url: string
  connected: boolean
  status: HookState
  last_text: string | null
  last_text_at: string | null
  error: string | null
}

export interface HookProbe {
  ok: boolean
  error: string | null
}

export interface HotkeyStatus {
  available: boolean
  note: string | null
  running: boolean
  hotkey: string | null
  captured: number
  last_error: string | null
  last_captured_at: string | null
}

export interface OverlayStatus {
  available: boolean
  note: string | null
  running: boolean
  visible: boolean
  last_error: string | null
  hotkey: string | null
  hotkey_running: boolean
}
