<script setup lang="ts">
import { computed } from 'vue'
import type { Analysis, DictEntry, KnownStatus, Span, Token } from '@/api/types'
import { headwordFor } from '@/utils/headword'

export interface PickedTerm {
  headword: string
  reading: string
  surface: string
  span_start: number
  span_end: number
  candidates: DictEntry[]
  term_id: number | null
  known_status: KnownStatus | null
  pos: string | null
  is_expression: boolean
}

const props = defineProps<{ analysis: Analysis; selectedStart?: number | null }>()
const emit = defineEmits<{ pick: [term: PickedTerm] }>()

interface Chip { key: string; text: string; token?: Token; span?: Span; content: boolean; status: KnownStatus | null; start: number }

const chips = computed<Chip[]>(() => {
  const out: Chip[] = []
  const spanByStart = new Map(props.analysis.spans.map((s) => [s.start_tok, s]))
  const tokens = props.analysis.tokens
  for (let i = 0; i < tokens.length; i++) {
    const span = spanByStart.get(i)
    if (span) {
      out.push({ key: `s${i}`, text: span.text, span, content: true, status: span.known_status, start: tokens[i]!.start })
      i = span.end_tok
      continue
    }
    const t = tokens[i]!
    out.push({ key: `t${i}`, text: t.surface, token: t, content: t.is_content, status: t.known_status, start: t.start })
  }
  return out
})

function cls(c: Chip) {
  if (!c.content) return 'text-ink-3'
  if (c.start === props.selectedStart) return 'bg-accent text-white'
  if (c.span) return 'bg-plum/15 text-plum hover:bg-plum/25'
  switch (c.status) {
    case 'known':
      return 'bg-matcha/10 text-matcha hover:bg-matcha/20'
    case 'learning':
      return 'bg-sky/10 text-sky hover:bg-sky/20'
    case 'ignored':
      return 'text-ink-3 line-through'
    default:
      return 'bg-accent/10 text-accent-2 hover:bg-accent/20'
  }
}

function pick(c: Chip) {
  if (!c.content) return
  if (c.span) {
    const first = c.span.candidates[0]
    const endTok = props.analysis.tokens[c.span.end_tok]!
    emit('pick', {
      headword: headwordFor(first, c.span.text, c.span.matched_form),
      reading: first?.reading ?? c.span.reading,
      surface: c.span.text,
      span_start: c.start,
      span_end: endTok.end,
      candidates: c.span.candidates,
      term_id: c.span.term_id,
      known_status: c.span.known_status,
      pos: first?.pos[0] ?? null,
      is_expression: true,
    })
    return
  }
  const t = c.token!
  const first = t.candidates[0]
  emit('pick', {
    headword: headwordFor(first, t.surface, t.base),
    reading: first?.reading ?? t.reading_base,
    surface: t.surface,
    span_start: t.start,
    span_end: t.end,
    candidates: t.candidates,
    term_id: t.term_id,
    known_status: t.known_status,
    pos: first?.pos[0] ?? t.pos1,
    is_expression: false,
  })
}
</script>

<template>
  <div class="jp flex flex-wrap gap-x-0.5 gap-y-1 text-lg leading-relaxed">
    <button
      v-for="c in chips"
      :key="c.key"
      type="button"
      class="rounded-md px-1 transition"
      :class="[cls(c), c.content ? 'cursor-pointer' : 'cursor-default']"
      :title="c.token ? `${c.token.base}（${c.token.reading_base}）${c.token.pos1}` : c.span ? `${c.span.matched_form}（${c.span.reading}）表达` : ''"
      @click="pick(c)"
    >
      {{ c.text }}
    </button>
  </div>
</template>
