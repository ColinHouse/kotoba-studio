/** 系统：设备、设置、词典、备份与用量。Instance-level payloads. */
import type { Owner } from './study'

export interface Device {
  id: string
  name: string
  kind: 'desktop' | 'mobile'
  created_at: string
  last_seen: string
}

export interface Settings {
  review_owner_default: Owner | null
  desired_retention: number
  fsrs_parameters: number[] | null
  fsrs_parameters_previous: number[] | null
  ai_provider: string
  ai_base_url: string
  ai_model: string
  ocr_provider: string
  active_session_id: number | null
  ui_language: string
}

export interface ConnectInfo {
  urls: string[]
  primary_url: string
  qr_svg: string
  port: number
  host: string
  lan_enabled: boolean
  hint: string | null
}

export interface DictStatus {
  installed: boolean
  dictionaries: {
    id: number
    title: string
    kind: string
    revision: string | null
    entry_count: number
    imported_at: string
  }[]
  install: { state: string; message: string; done: number; total: number }
}

export interface Backup {
  name: string
  size: number
  created_at: string
}

export interface CardStats {
  total: number
  new: number
  due_now: number
  streak_days: number
  by_owner: Record<string, number>
  by_state: Record<string, number>
}

export interface AiUsage {
  calls: number
  failed: number
  prompt_tokens: number
  completion_tokens: number
  cost_estimate_usd: number
  by_model: { model: string; calls: number; cost_estimate_usd: number }[]
}
