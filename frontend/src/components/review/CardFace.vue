<script setup lang="ts">
import { computed } from 'vue'
import { mediaUrl } from '@/api/client'
import type { CardFace } from '@/api/types'
import ExplanationBlock from './ExplanationBlock.vue'
import { CARD_TYPE_LABEL } from '@/utils/format'

const props = defineProps<{ face: CardFace; revealed: boolean }>()

const sentenceParts = computed(() => {
  const enc = props.face.encounter
  if (!enc) return null
  const t = enc.line_text
  const s = enc.span_start
  const e = enc.span_end
  if (s >= 0 && e <= t.length && t.slice(s, e) === enc.surface)
    return { before: t.slice(0, s), hit: enc.surface, after: t.slice(e) }
  const idx = t.indexOf(enc.surface)
  if (idx >= 0)
    return { before: t.slice(0, idx), hit: enc.surface, after: t.slice(idx + enc.surface.length) }
  return { before: t, hit: '', after: '' }
})

const glosses = computed(
  () => props.face.term.senses.map((s) => s.gloss_zh || s.gloss_en).filter(Boolean) as string[],
)
</script>

<template>
  <div class="card p-5 md:p-7">
    <div class="mb-3 flex items-center justify-between text-xs text-ink-3">
      <span
        >{{ CARD_TYPE_LABEL[face.card_type] }}卡 · {{ face.encounter?.source_title ?? '—' }}</span
      >
      <span v-if="face.other_encounters">另在 {{ face.other_encounters }} 处遇见过</span>
    </div>

    <!-- front -->
    <div class="text-center">
      <template v-if="face.card_type === 'cloze'">
        <p class="jp text-2xl leading-relaxed md:text-3xl">{{ face.cloze_text }}</p>
        <p class="mt-2 text-sm text-ink-3">空缺处是什么？</p>
      </template>
      <template v-else-if="face.card_type === 'listening'">
        <audio
          v-if="face.encounter?.audio_path"
          :src="mediaUrl(face.encounter.audio_path)"
          controls
          class="mx-auto"
        />
        <p class="mt-2 text-sm text-ink-3">听原声，回忆这句里的目标词</p>
      </template>
      <template v-else>
        <p class="jp text-4xl font-semibold md:text-5xl">{{ face.term.headword }}</p>
        <p v-if="face.card_type === 'meaning' && face.term.reading" class="jp mt-1 text-ink-2">
          {{ face.term.reading }}
        </p>
        <p class="mt-2 text-sm text-ink-3">
          {{ face.card_type === 'reading' ? '怎么读？在这句里是什么意思？' : '什么意思？' }}
        </p>
      </template>
    </div>

    <!-- back -->
    <div v-if="revealed" class="mt-5 space-y-4 border-t border-line pt-5">
      <div class="text-center">
        <p class="jp text-3xl font-semibold">{{ face.term.headword }}</p>
        <p class="jp text-lg text-accent-2">{{ face.term.reading }}</p>
      </div>
      <ul v-if="glosses.length" class="space-y-1 text-center text-base">
        <li v-for="(g, i) in glosses" :key="i">{{ g }}</li>
      </ul>
      <div
        v-if="face.term.trap"
        class="rounded-xl border border-accent/30 bg-accent/10 p-3 text-sm"
      >
        <span class="label text-accent-2">中日同形 · 注意</span>
        <p>
          中文「{{ face.term.trap.headword }}」＝{{
            face.term.trap.zh_reading_meaning
          }}；日语＝<b>{{ face.term.trap.ja_meaning }}</b
          >。{{ face.term.trap.note }}
        </p>
      </div>
      <div v-if="sentenceParts" class="jp rounded-xl bg-paper-2 p-3 text-lg leading-relaxed">
        {{ sentenceParts.before }}<b class="text-accent-2">{{ sentenceParts.hit }}</b
        >{{ sentenceParts.after }}
        <p v-if="face.encounter?.contraction_of" class="mt-1 text-sm text-ink-2">
          缩约形 ← {{ face.encounter.contraction_of }}
        </p>
      </div>
      <img
        v-if="face.encounter?.screenshot_path"
        :src="mediaUrl(face.encounter.screenshot_path)"
        class="mx-auto max-h-64 rounded-xl border border-line"
        alt="截图"
      />
      <audio
        v-if="face.card_type !== 'listening' && face.encounter?.audio_path"
        :src="mediaUrl(face.encounter.audio_path)"
        controls
        class="mx-auto"
      />
      <ExplanationBlock
        v-if="face.encounter?.ai_explanation"
        :explanation="face.encounter.ai_explanation"
      />
    </div>
  </div>
</template>
