<script setup lang="ts">
import { computed } from 'vue'
import { mediaUrl } from '@/api/client'
import type { CardFace } from '@/api/types'
import Furigana from '@/components/common/Furigana.vue'
import ExplanationBlock from './ExplanationBlock.vue'
import PitchLine from './PitchLine.vue'
import TrapBlock from './TrapBlock.vue'
import { CARD_TYPE_LABEL } from '@/utils/format'

const props = defineProps<{ face: CardFace; revealed: boolean }>()

/** 原句拆成三段，中间那段是这次要学的词。 */
const sentence = computed(() => {
  const enc = props.face.encounter
  if (!enc) return null
  const text = enc.line_text
  const { span_start: s, span_end: e, surface } = enc
  if (s >= 0 && e <= text.length && text.slice(s, e) === surface) {
    return { before: text.slice(0, s), target: surface, after: text.slice(e) }
  }
  const idx = surface ? text.indexOf(surface) : -1
  if (idx >= 0) {
    return { before: text.slice(0, idx), target: surface, after: text.slice(idx + surface.length) }
  }
  return { before: text, target: '', after: '' }
})

const glosses = computed(
  () => props.face.term.senses.map((s) => s.gloss_zh || s.gloss_en).filter(Boolean) as string[],
)
const source = computed(() => props.face.encounter?.source_title ?? '—')
const prompt = computed(
  () =>
    ({
      reading: '怎么读？在这句里是什么意思？',
      meaning: '什么意思？',
      cloze: '空缺处是什么？',
      listening: '听原声，回忆这句里的目标词',
    })[props.face.card_type],
)
</script>

<template>
  <article class="lifted overflow-hidden">
    <!-- 正反面用 out-in：旧的先退干净再进新的。同时在场哪怕一帧，
         正面也就泄露答案了（不变量 §5.2）。 -->
    <Transition name="fade" mode="out-in">
      <!-- ── 正面：绝不出现截图，也不出现含答案的整句 ─────────────────── -->
      <div v-if="!revealed" class="px-6 pt-[30px] pb-7 md:px-[30px]">
        <header class="flex items-baseline justify-between">
          <span class="kicker text-accent">{{ CARD_TYPE_LABEL[face.card_type] }}卡</span>
          <span class="kicker tracking-[0.1em]">{{ source }}</span>
        </header>

        <div
          v-if="face.card_type === 'cloze'"
          class="jp my-5 text-[26px] leading-[2] md:text-[29px]"
        >
          <template v-if="face.cloze_text">{{ face.cloze_text }}</template>
        </div>
        <div v-else-if="face.card_type === 'listening'" class="py-8 text-center">
          <audio
            v-if="face.encounter?.audio_path"
            :src="mediaUrl(face.encounter.audio_path)"
            controls
            class="mx-auto"
          />
          <p v-else class="m-0 type-note text-ink-35">这张卡还没有音频。</p>
        </div>
        <div v-else class="py-6 text-center">
          <p
            class="jp m-0 tracking-[0.02em]"
            :class="
              face.card_type === 'reading'
                ? 'text-[62px] md:text-[76px]'
                : 'text-[52px] md:text-[62px]'
            "
            style="line-height: 1.3"
          >
            {{ face.term.headword }}
          </p>
          <p
            v-if="face.card_type === 'meaning' && face.term.reading"
            class="jp mt-1 mb-0 text-[19px] text-ink-50"
          >
            （{{ face.term.reading }}）
          </p>
        </div>

        <div class="h-px bg-divider" />
        <p
          class="mt-3.5 mb-0 type-body leading-[1.7] text-ink-70"
          :class="face.card_type === 'cloze' ? '' : 'text-center'"
        >
          {{ prompt }}
        </p>
      </div>

      <!-- ── 背面：揭晓 → 同形 → 语境 → 注释 ───────────────────────────── -->
      <div v-else class="md:grid md:grid-cols-[1fr_1px_1fr]">
        <div class="min-w-0">
          <div class="reveal-step px-6 pt-[22px] pb-5 md:px-[30px] md:pt-7" style="--step: 0">
            <header class="flex items-baseline justify-between">
              <span class="kicker text-accent">{{ CARD_TYPE_LABEL[face.card_type] }}卡 · 揭晓</span>
              <span class="kicker tracking-[0.1em]">{{ source }}</span>
            </header>
            <p class="mt-2.5 mb-0 text-[46px] leading-[1.7] tracking-[0.02em] md:text-[58px]">
              <Furigana
                :word="face.term.headword"
                :reading="face.term.reading"
                class="reveal-ruby"
              />
            </p>
            <p v-if="glosses.length" class="mt-1.5 mb-0 text-[19px] leading-[1.6] md:text-[21px]">
              {{ glosses.join('；') }}
            </p>
            <p v-else class="mt-1.5 mb-0 type-body text-ink-35">还没有填释义。</p>
            <div v-if="face.pitches.length" class="mt-3.5 flex flex-wrap gap-x-5 gap-y-2">
              <PitchLine
                v-for="p in face.pitches"
                :key="`${p.reading}-${p.accent}`"
                :reading="p.reading"
                :accent="p.accent"
                :label="p.label"
              />
            </div>
          </div>

          <TrapBlock
            v-if="face.term.trap"
            :trap="face.term.trap"
            class="reveal-step md:mx-[30px] md:mb-7"
            style="--step: 1"
            :framed="true"
          />
        </div>

        <div class="hidden bg-divider md:block" />

        <div class="min-w-0">
          <div class="reveal-step px-6 pt-5 pb-[18px] md:px-[30px] md:pt-7" style="--step: 2">
            <p class="kicker mb-3">原句</p>
            <p v-if="sentence" class="jp m-0 mb-3.5 text-[21px] leading-[2.1] md:text-[24px]">
              {{ sentence.before
              }}<b v-if="sentence.target" class="target"
                ><Furigana :word="sentence.target" :reading="face.term.reading" /></b
              >{{ sentence.after }}
            </p>
            <img
              v-if="face.encounter?.screenshot_path"
              :src="mediaUrl(face.encounter.screenshot_path)"
              class="plate w-full rounded-chip"
              alt="这句台词的截图"
            />
            <audio
              v-if="face.card_type !== 'listening' && face.encounter?.audio_path"
              :src="mediaUrl(face.encounter.audio_path)"
              controls
              class="mt-2.5 w-full"
            />
            <div class="mt-2.5 flex items-baseline justify-between gap-3 type-meta text-ink-50">
              <span v-if="face.encounter?.contraction_of" class="jp"
                >{{ face.encounter.surface }} ← {{ face.encounter.contraction_of }}</span
              >
              <span v-else />
              <span v-if="face.other_encounters" class="num shrink-0"
                >另在 {{ face.other_encounters }} 处遇见过 →</span
              >
            </div>
          </div>

          <ExplanationBlock
            v-if="face.encounter?.ai_explanation"
            :explanation="face.encounter.ai_explanation"
            class="reveal-step"
            style="--step: 3"
          />
        </div>
      </div>
    </Transition>
  </article>
</template>

<style scoped>
/* 揭晓时的注音用金色，和界面里的灰注音区分开：这是答案。 */
.reveal-ruby :deep(rt) {
  color: var(--accent);
  font-size: 0.32em;
}
.target {
  font-weight: 600;
  color: var(--gold-deep);
  border-bottom: 2px solid var(--accent);
  padding-bottom: 1px;
}
.target :deep(rt) {
  font-size: 0.36em;
  color: var(--gold-deep);
}
</style>
