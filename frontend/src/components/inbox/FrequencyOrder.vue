<script setup lang="ts">
import { computed } from 'vue'
import type { Token } from '@/api/types'
import Furigana from '@/components/common/Furigana.vue'
import type { PickedTerm } from './TokenChips.vue'
import { byFrequency, frequencyBand } from '@/utils/frequency'

const props = defineProps<{ tokens: Token[] }>()
const emit = defineEmits<{ pick: [term: PickedTerm] }>()

/** The line's unknown words, deduped, most common first: i.e. what to learn first. */
const unknown = computed(() => {
  const seen = new Set<string>()
  const out: Token[] = []
  for (const token of props.tokens) {
    if (!token.is_content) continue
    if (token.term_id !== null && token.known_status !== 'unknown') continue
    if (seen.has(token.base)) continue
    seen.add(token.base)
    out.push(token)
  }
  return byFrequency(out)
})

function pick(token: Token) {
  const first = token.candidates[0]
  emit('pick', {
    headword: first?.headword ?? token.base,
    reading: first?.reading ?? token.reading_base,
    surface: token.surface,
    span_start: token.start,
    span_end: token.end,
    candidates: token.candidates,
    term_id: token.term_id,
    known_status: token.known_status,
    pos: first?.pos[0] ?? token.pos1,
    is_expression: false,
  })
}
</script>

<template>
  <section v-if="unknown.length" class="framed p-3">
    <p class="kicker m-0">这句先学哪个 · 越常见越靠前</p>
    <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
      <button
        v-for="token in unknown"
        :key="token.start"
        type="button"
        class="flex items-center gap-1.5 border-0 bg-transparent p-0"
        @click="pick(token)"
      >
        <span class="tag tag-state" :class="frequencyBand(token.frequency_rank).className">
          {{ frequencyBand(token.frequency_rank).label }}
        </span>
        <span class="jp text-[18px] leading-[1.6]">
          <Furigana :word="token.surface" :reading="token.reading" />
        </span>
      </button>
    </div>
  </section>
</template>
