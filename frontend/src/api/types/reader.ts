/** 阅读：按页取出的漫画文本块。Reader payloads. */

export interface ReaderBlock {
  line_id: number
  text: string
  box: [number, number, number, number]
  status: 'inbox' | 'kept' | 'discarded'
  encounter_count: number
  card_count: number
}

export interface ReaderPage {
  page: number
  image: string | null
  blocks: ReaderBlock[]
}

export interface ReaderPages {
  source_id: number
  title: string
  title_ja: string | null
  pages: ReaderPage[]
}
