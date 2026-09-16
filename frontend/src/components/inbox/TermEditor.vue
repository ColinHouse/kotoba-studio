<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { CardType, DictEntry } from '@/api/types'
import type { PickedTerm } from './TokenChips.vue'
import { CARD_TYPE_LABEL } from '@/utils/format'
import { headwordFor } from '@/utils/headword'
import { hasKanji } from '@/utils/kana'

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

const headword = ref('')
const reading = ref('')
const glossZh = ref('')
const glossEn = ref('')
const cardTypes = ref<CardType[]>([])
const candidate = ref<DictEntry | null>(null)

const OFFERED_TYPES: CardType[] = ['reading', 'meaning', 'cloze']

/** A kanji headword is worth a reading card; a kana one is not. */
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

const canConfirm = computed(() => headword.value.trim().length > 0)

function confirm() {
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
    sense: zh || en ? { gloss_zh: zh || null, gloss_en: en || null, origin: zh ? 'user' : 'jmdict' } : null,
    card_types: cardTypes.value,
  })
}
</script>

<template>
  <div class="card space-y-3 p-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <p class="jp text-xl font-semibold">
        {{ picked.surface }}
        <span class="text-sm font-normal text-ink-3">
          {{ picked.is_expression ? '表达' : (picked.pos ?? '') }}
        </span>
      </p>
      <span v-if="picked.known_status" class="text-xs text-ink-3">
        已在词库：{{ picked.known_status }}
      </span>
    </div>

    <div v-if="picked.candidates.length" class="space-y-1">
      <p class="label">词典候选</p>
      <button
        v-for="entry in picked.candidates"
        :key="entry.id"
        type="button"
        class="block w-full rounded-lg border px-3 py-2 text-left text-sm"
        :class="candidate?.id === entry.id ? 'border-accent bg-accent/10' : 'border-line'"
        @click="chooseCandidate(entry)"
      >
        <span class="jp font-semibold">{{ entry.headword }}</span>
        <span class="jp text-ink-2"> {{ entry.reading }}</span>
        <span v-if="entry.common" class="chip ml-1 bg-matcha/15 text-[10px] text-matcha">常用</span>
        <span class="block text-ink-2">{{ entry.senses[0]?.gloss_en.slice(0, 3).join('; ') }}</span>
      </button>
    </div>

    <div class="grid gap-2 sm:grid-cols-2">
      <label class="text-sm" for="term-headword">
        <span class="label">词条</span>
        <input id="term-headword" v-model="headword" class="input jp" />
      </label>
      <label class="text-sm" for="term-reading">
        <span class="label">读音</span>
        <input id="term-reading" v-model="reading" class="input jp" />
      </label>
      <label class="text-sm sm:col-span-2" for="term-gloss-zh">
        <span class="label">中文释义（这里的意思）</span>
        <input id="term-gloss-zh" v-model="glossZh" class="input" placeholder="例如：请客、宴请" />
      </label>
      <label class="text-sm sm:col-span-2" for="term-gloss-en">
        <span class="label">英文释义（词典）</span>
        <input id="term-gloss-en" v-model="glossEn" class="input" />
      </label>
    </div>

    <div class="flex flex-wrap items-center gap-3 text-sm">
      <span class="label">卡片</span>
      <label v-for="type in OFFERED_TYPES" :key="type" class="flex items-center gap-1">
        <input v-model="cardTypes" type="checkbox" :value="type" />{{ CARD_TYPE_LABEL[type] }}
      </label>
    </div>

    <div class="flex gap-2">
      <button class="btn-primary" :disabled="!canConfirm || busy" @click="confirm">
        {{ cardTypes.length ? '确认并建卡' : '只记录语境' }}
      </button>
      <button class="btn-ghost" @click="$emit('cancel')">取消</button>
    </div>
  </div>
</template>
