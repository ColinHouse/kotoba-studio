<script setup lang="ts">
import { computed } from 'vue'
import type { Analysis, DictEntry, KnownStatus, Span, Token } from '@/api/types'
import Furigana from '@/components/common/Furigana.vue'

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

const props = defineProps<{ analysis: Analysis; selectedStart?: number | null; legend?: boolean }>()
const emit = defineEmits<{ pick: [term: PickedTerm] }>()

interface Chip {
  key: string
  text: string
  reading: string
  token?: Token
  span?: Span
  content: boolean
  status: KnownStatus | null
  start: number
}

const chips = computed<Chip[]>(() => {
  const out: Chip[] = []
  const spanByStart = new Map(props.analysis.spans.map((s) => [s.start_tok, s]))
  const tokens = props.analysis.tokens
  for (let i = 0; i < tokens.length; i++) {
    const span = spanByStart.get(i)
    if (span) {
      out.push({
        key: `s${i}`,
        text: span.text,
        reading: span.reading,
        span,
        content: true,
        status: span.known_status,
        start: tokens[i]!.start,
      })
      i = span.end_tok
      continue
    }
    const t = tokens[i]!
    out.push({
      key: `t${i}`,
      text: t.surface,
      reading: t.reading,
      token: t,
      content: t.is_content,
      status: t.known_status,
      start: t.start,
    })
  }
  return out
})

/** 状态用墨色浓淡 + 线型编码，颜色只留给"当前选中"和动作。 */
function chipClass(c: Chip): string {
  if (!c.content) return 'tok tok-plain'
  if (c.start === props.selectedStart) return 'tok tok-selected'
  if (c.span) return 'tok tok-expression'
  switch (c.status) {
    case 'known':
      return 'tok tok-known'
    case 'learning':
      return 'tok tok-learning'
    case 'ignored':
      return 'tok tok-ignored'
    default:
      return 'tok tok-unknown'
  }
}

function pick(c: Chip) {
  if (!c.content) return
  if (c.span) {
    const first = c.span.candidates[0]
    const endTok = props.analysis.tokens[c.span.end_tok]!
    emit('pick', {
      headword: first?.headword ?? c.span.matched_form,
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
    headword: first?.headword ?? t.base,
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
  <div>
    <div
      class="jp flex flex-wrap items-baseline text-[24px] leading-[2.5] md:text-[30px] md:leading-[2.4]"
    >
      <component
        :is="c.content ? 'button' : 'span'"
        v-for="c in chips"
        :key="c.key"
        :type="c.content ? 'button' : undefined"
        :class="chipClass(c)"
        :title="
          c.span
            ? `${c.span.matched_form}（${c.span.reading}）· 固定表达`
            : c.token
              ? `${c.token.base}（${c.token.reading_base}）${c.token.pos1}`
              : undefined
        "
        @click="pick(c)"
      >
        <Furigana v-if="c.content" :word="c.text" :reading="c.reading" />
        <template v-else>{{ c.text }}</template>
      </component>
    </div>

    <div
      v-if="legend"
      class="mt-4 flex flex-wrap items-center gap-x-[18px] gap-y-1.5 type-micro text-ink-50"
    >
      <span class="kicker">读法</span>
      <span
        ><b class="text-ink" style="border-bottom: 2px solid var(--ink)">深墨＋实线</b>
        未学，要点的</span
      >
      <span
        ><span class="text-ink-70" style="border-bottom: 1px dashed var(--ink-50)">中墨＋虚线</span>
        学习中</span
      >
      <span><span class="font-light text-ink-50">浅墨</span> 已掌握</span>
      <span
        ><span class="rounded-chip border border-divider px-1">方框</span>
        固定表达，整块算一个词</span
      >
    </div>
  </div>
</template>
