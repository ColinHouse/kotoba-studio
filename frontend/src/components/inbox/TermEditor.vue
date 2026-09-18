<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { CardType, DictEntry } from '@/api/types'
import type { PickedTerm } from './TokenChips.vue'
import { senseOrigin } from '@/utils/dictionaries'
import { CARD_TYPE_LABEL } from '@/utils/format'
import { headwordFor } from '@/utils/headword'
import { hasKanji } from '@/utils/kana'
import { confirmShortcut } from '@/utils/platform'

export interface ConfirmPayload {
  headword: string
  reading: string
  surface: string
  span_start: number
  span_end: number
  pos: string | null
  jmdict_id: string | null
  sense: { gloss_zh: string | null; gloss_en: string | null; origin: string } | null
  card_types: CardType[]
}

const props = defineProps<{ picked: PickedTerm; busy: boolean }>()
const emit = defineEmits<{ confirm: [payload: ConfirmPayload]; cancel: [] }>()

const shortcut = confirmShortcut(navigator.userAgent)

const headword = ref('')
const reading = ref('')
const glossZh = ref('')
const glossEn = ref('')
const cardTypes = ref<CardType[]>([])
const candidate = ref<DictEntry | null>(null)

const OFFERED: CardType[] = ['reading', 'meaning', 'cloze']

/** 含汉字的词值得一张读音卡；假名词不值得。 */
function defaultTypes(word: string): CardType[] {
  return hasKanji(word) ? ['reading', 'cloze'] : ['meaning', 'cloze']
}

watch(
  () => props.picked,
  (picked) => {
    const first = picked.candidates[0] ?? null
    candidate.value = first
    headword.value = picked.headword
    reading.value = picked.reading
    glossZh.value = ''
    glossEn.value = first?.senses[0]?.gloss_en.slice(0, 3).join('; ') ?? ''
    cardTypes.value = defaultTypes(picked.headword)
  },
  { immediate: true },
)

function chooseCandidate(entry: DictEntry) {
  candidate.value = entry
  headword.value = headwordFor(entry, props.picked.surface, entry.headword)
  reading.value = entry.reading
  glossEn.value = entry.senses[0]?.gloss_en.slice(0, 3).join('; ') ?? ''
  cardTypes.value = defaultTypes(headword.value)
}

function toggle(type: CardType) {
  cardTypes.value = cardTypes.value.includes(type)
    ? cardTypes.value.filter((t) => t !== type)
    : [...cardTypes.value, type]
}

const canConfirm = computed(() => headword.value.trim().length > 0)

function confirm() {
  if (!canConfirm.value) return
  const zh = glossZh.value.trim()
  const en = glossEn.value.trim()
  emit('confirm', {
    headword: headword.value.trim(),
    reading: reading.value.trim(),
    surface: props.picked.surface,
    span_start: props.picked.span_start,
    span_end: props.picked.span_end,
    pos: props.picked.pos,
    jmdict_id: candidate.value?.id ?? null,
    sense:
      zh || en
        ? {
            gloss_zh: zh || null,
            gloss_en: en || null,
            origin: senseOrigin(candidate.value, !!zh),
          }
        : null,
    card_types: cardTypes.value,
  })
}

function onKey(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault()
    confirm()
  } else if (e.key === 'Escape') {
    emit('cancel')
  }
}
</script>

<template>
  <section class="lifted px-6 py-[22px]" @keydown="onKey">
    <header class="flex items-baseline justify-between gap-3 border-b border-divider pb-3">
      <div class="flex items-baseline gap-2.5">
        <span class="jp text-[24px] font-semibold md:text-[26px]">{{ picked.surface }}</span>
        <span class="type-meta text-ink-35">
          {{ picked.is_expression ? '固定表达' : (picked.pos ?? '') }}
        </span>
      </div>
      <span class="shrink-0 type-micro text-ink-35">
        {{ picked.known_status ? `词库中：${picked.known_status}` : '尚未在词库' }}
      </span>
    </header>

    <div class="mt-4 grid gap-[22px] md:grid-cols-2">
      <div v-if="picked.candidates.length">
        <p class="kicker mb-2">词典候选</p>
        <button
          v-for="entry in picked.candidates"
          :key="entry.id"
          type="button"
          class="mb-1.5 block w-full rounded-chip border px-[11px] py-[9px] text-left last:mb-0"
          :class="
            candidate?.id === entry.id
              ? 'border-accent bg-accent-100'
              : 'border-divider hover:bg-surface/60'
          "
          @click="chooseCandidate(entry)"
        >
          <span class="flex flex-wrap items-baseline gap-2">
            <span
              class="jp text-[17px] font-semibold"
              :class="candidate?.id === entry.id ? 'text-accent-800' : 'text-ink'"
              >{{ entry.headword }}</span
            >
            <span
              class="jp type-note"
              :class="candidate?.id === entry.id ? 'text-gold' : 'text-ink-50'"
              >{{ entry.reading }}</span
            >
            <span v-if="entry.common" class="tag tag-warn" style="font-size: 10px; padding: 1px 7px"
              >常用</span
            >
          </span>
          <span
            class="mt-0.5 block type-meta leading-snug"
            :class="candidate?.id === entry.id ? 'text-gold' : 'text-ink-50'"
            >{{ entry.senses[0]?.gloss_en.slice(0, 3).join('; ') }}</span
          >
        </button>
      </div>
      <p v-else class="m-0 type-meta text-ink-35">词典里没有候选，请手填词条与释义。</p>

      <div class="flex flex-col gap-3">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="field-label" for="term-headword">词条</label>
            <input id="term-headword" v-model="headword" class="input jp" style="font-size: 16px" />
          </div>
          <div>
            <label class="field-label" for="term-reading">读音</label>
            <input id="term-reading" v-model="reading" class="input jp" style="font-size: 16px" />
          </div>
        </div>
        <div>
          <label class="field-label" for="term-gloss-zh">中文释义（这里的意思）</label>
          <input
            id="term-gloss-zh"
            v-model="glossZh"
            class="input"
            placeholder="例如：请客、宴请"
          />
        </div>
        <div>
          <label class="field-label" for="term-gloss-en">
            词典释义
            <span v-if="candidate" class="text-ink-35">· {{ candidate.dict_title }}</span>
          </label>
          <input id="term-gloss-en" v-model="glossEn" class="input" />
        </div>
        <div>
          <p class="mb-1.5 type-meta text-ink-50">建哪几张卡</p>
          <div class="seg">
            <button
              v-for="type in OFFERED"
              :key="type"
              type="button"
              class="seg-opt"
              :aria-pressed="cardTypes.includes(type)"
              @click="toggle(type)"
            >
              {{ CARD_TYPE_LABEL[type] }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <footer class="mt-5 flex flex-wrap items-center gap-3 border-t border-rule pt-4">
      <button class="btn btn-primary" :disabled="!canConfirm || busy" @click="confirm">
        {{ cardTypes.length ? '确认并建卡' : '只记录语境' }}
      </button>
      <button class="btn btn-secondary" @click="$emit('cancel')">取消</button>
      <span class="num ml-auto hidden type-micro text-ink-35 md:inline"
        >{{ shortcut }} 确认 · Esc 取消</span
      >
    </footer>
  </section>
</template>
