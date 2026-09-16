<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { Card, Encounter, Explanation, KnownStatus, Owner, TermDetail } from '@/api/types'
import ExplanationBlock from '@/components/review/ExplanationBlock.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useAppStore } from '@/stores/app'
import { CARD_TYPE_LABEL, fmtDateTime, humanInterval, STATUS_LABEL } from '@/utils/format'

const props = defineProps<{ id: string }>()
const app = useAppStore()
const term = ref<TermDetail | null>(null)
const explaining = ref<number | null>(null)

async function load() {
  term.value = await api.get<TermDetail>(`/api/terms/${props.id}`)
}
onMounted(() => load().catch(app.fail))

async function setStatus(status: KnownStatus) {
  try {
    term.value = await api.patch<TermDetail>(`/api/terms/${props.id}`, { known_status: status })
  } catch (e) {
    app.fail(e)
  }
}

async function setOwner(card: Card, owner: Owner) {
  try {
    await api.patch(`/api/cards/${card.id}`, { review_owner: owner })
    await load()
  } catch (e) {
    app.fail(e)
  }
}

async function explain(enc: Encounter, force = false) {
  explaining.value = enc.id
  try {
    const r = await api.post<{ explanation: Explanation }>('/api/ai/explain', { encounter_id: enc.id, force })
    enc.ai_explanation = r.explanation
  } catch (e) {
    app.fail(e)
  } finally {
    explaining.value = null
  }
}
</script>

<template>
  <div v-if="term" class="mx-auto max-w-4xl space-y-6">
    <RouterLink to="/library" class="text-sm text-accent-2">← 词库</RouterLink>
    <header class="card p-5">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="jp text-4xl font-semibold">{{ term.headword }}</p>
          <p class="jp text-lg text-accent-2">{{ term.reading }} <span class="text-sm text-ink-3">{{ term.pos ?? '' }}</span></p>
        </div>
        <div class="flex flex-wrap gap-1">
          <button v-for="(label, k) in STATUS_LABEL" :key="k" class="btn-ghost text-xs" :class="{ 'ring-2 ring-accent': term.known_status === k }" @click="setStatus(k as KnownStatus)">{{ label }}</button>
        </div>
      </div>
      <ul class="mt-3 space-y-1">
        <li v-for="s in term.senses" :key="s.id" class="text-base">{{ s.gloss_zh || s.gloss_en }} <span class="text-xs text-ink-3">{{ s.origin }}</span></li>
      </ul>
      <div v-if="term.trap" class="mt-3 rounded-xl border border-accent/30 bg-accent/10 p-3 text-sm">
        <span class="label text-accent-2">中日同形异义</span>
        <p>中文「{{ term.trap.headword }}」＝{{ term.trap.zh_reading_meaning }}；日语＝<b>{{ term.trap.ja_meaning }}</b>。{{ term.trap.note }}</p>
      </div>
      <p class="mt-3 text-xs text-ink-3">遇见 {{ term.encounter_count }} 次 · {{ term.source_count }} 部作品 · {{ term.card_count }} 张卡 · <StatusBadge :status="term.known_status" /></p>
    </header>

    <section>
      <h2 class="mb-2 font-semibold">语境时间线</h2>
      <ol class="space-y-3">
        <li v-for="enc in term.encounters" :key="enc.id" class="card p-4">
          <div class="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-3">
            <span>{{ enc.source_title ?? '未归档' }} · {{ fmtDateTime(enc.captured_at) }}</span>
            <span v-if="enc.contraction_of">缩约形「{{ enc.surface }}」← {{ enc.contraction_of }}</span>
          </div>
          <p class="jp mt-1 text-lg leading-relaxed">{{ enc.line_text }}</p>
          <div class="mt-2 flex flex-col gap-3 md:flex-row">
            <img v-if="enc.screenshot_path" :src="mediaUrl(enc.screenshot_path)" class="max-h-40 rounded-lg border border-line md:w-64 md:object-cover" alt="截图" />
            <div class="flex-1 space-y-2">
              <ExplanationBlock v-if="enc.ai_explanation" :explanation="enc.ai_explanation" />
              <div class="flex gap-2">
                <button class="btn-outline text-xs" :disabled="explaining === enc.id" @click="explain(enc, !!enc.ai_explanation)">{{ explaining === enc.id ? '解释中…' : enc.ai_explanation ? '重新解释' : 'AI 解释这句' }}</button>
                <RouterLink :to="`/inbox?session=${enc.line_id}`" class="hidden" />
              </div>
            </div>
          </div>
        </li>
      </ol>
    </section>

    <section>
      <h2 class="mb-2 font-semibold">卡片</h2>
      <ul class="card divide-y divide-line">
        <li v-for="c in term.cards" :key="c.id" class="flex flex-wrap items-center justify-between gap-2 px-4 py-2 text-sm">
          <span>{{ CARD_TYPE_LABEL[c.card_type] }}卡 · {{ c.due ? `到期 ${humanInterval(c.due)}后` : '新卡' }}<span v-if="c.stability"> · 稳定性 {{ c.stability.toFixed(1) }} 天</span></span>
          <span class="flex items-center gap-1 text-xs">
            归属
            <button v-for="o in (['desktop', 'mobile', 'any'] as Owner[])" :key="o" class="btn-ghost px-2 py-1 text-xs" :class="{ 'ring-2 ring-accent': c.review_owner === o }" @click="setOwner(c, o)">{{ { desktop: '电脑', mobile: '手机', any: '任意' }[o] }}</button>
          </span>
        </li>
        <li v-if="!term.cards.length" class="px-4 py-3 text-sm text-ink-2">还没有卡片。在收件箱确认这个词时勾选卡片类型。</li>
      </ul>
    </section>
  </div>
</template>
