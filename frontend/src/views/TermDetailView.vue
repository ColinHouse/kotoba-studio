<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { Card, Encounter, Explanation, KnownStatus, Owner, TermDetail } from '@/api/types'
import Furigana from '@/components/common/Furigana.vue'
import ExplanationBlock from '@/components/review/ExplanationBlock.vue'
import TrapBlock from '@/components/review/TrapBlock.vue'
import { useAppStore } from '@/stores/app'
import { originLabel } from '@/utils/dictionaries'
import { CARD_TYPE_LABEL, humanInterval, STATUS_LABEL } from '@/utils/format'

const props = defineProps<{ id: string }>()
const app = useAppStore()
const term = ref<TermDetail | null>(null)
const explaining = ref<number | null>(null)

const STATUSES = Object.keys(STATUS_LABEL) as KnownStatus[]
const OWNERS: { value: Owner; label: string }[] = [
  { value: 'desktop', label: '电脑' },
  { value: 'mobile', label: '手机' },
  { value: 'any', label: '任意' },
]

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
    const r = await api.post<{ explanation: Explanation }>('/api/ai/explain', {
      encounter_id: enc.id,
      force,
    })
    enc.ai_explanation = r.explanation
  } catch (e) {
    app.fail(e)
  } finally {
    explaining.value = null
  }
}

function dayLabel(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}
function timeLabel(iso: string) {
  return new Date(iso).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function sentenceParts(enc: Encounter) {
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
}
</script>

<template>
  <div v-if="term">
    <RouterLink to="/library" class="text-[12px] text-accent no-underline">← 词库</RouterLink>

    <header
      class="mt-4 flex flex-wrap items-start justify-between gap-6 border-b border-divider pb-5"
    >
      <div class="min-w-0">
        <p class="m-0 text-[44px] leading-[1.7] tracking-[0.02em] md:text-[58px]">
          <Furigana :word="term.headword" :reading="term.reading" class="head-ruby" />
        </p>
        <div class="mt-0.5 flex flex-wrap items-baseline gap-3">
          <span class="text-[19px]">{{
            term.senses
              .map((s) => s.gloss_zh)
              .filter(Boolean)
              .join('；') || '还没有中文释义'
          }}</span>
          <span v-if="term.pos" class="text-[12px] text-ink-35">{{ term.pos }}</span>
        </div>
        <p v-if="term.senses.some((s) => s.gloss_en)" class="mt-1.5 mb-0 text-[13px] text-ink-50">
          <template v-for="(s, i) in term.senses.filter((x) => x.gloss_en)" :key="s.id">
            <span v-if="i" class="text-ink-35">; </span>{{ s.gloss_en }}
            <span class="text-[11px] text-ink-35">{{ originLabel(s.origin) }}</span>
          </template>
        </p>
      </div>
      <div class="shrink-0 md:text-right">
        <div class="seg">
          <button
            v-for="s in STATUSES"
            :key="s"
            type="button"
            class="seg-opt"
            :aria-pressed="term.known_status === s"
            @click="setStatus(s)"
          >
            {{ STATUS_LABEL[s] }}
          </button>
        </div>
        <p class="num mt-2.5 mb-0 text-[11px] text-ink-35">
          遇见 {{ term.encounter_count }} 次 · {{ term.source_count }} 部作品 ·
          {{ term.card_count }} 张卡
        </p>
      </div>
    </header>

    <Transition name="rise">
      <TrapBlock v-if="term.trap" :trap="term.trap" :framed="true" class="mt-5" />
    </Transition>

    <section class="mt-[26px]">
      <div class="flex flex-wrap items-baseline gap-3">
        <h2 class="m-0 font-head text-[22px] font-normal">相遇史</h2>
        <span v-if="term.encounters.length" class="text-[12px] text-ink-50">
          最早在 {{ dayLabel(term.encounters[0]!.captured_at) }}，最近是
          {{ dayLabel(term.encounters[term.encounters.length - 1]!.captured_at) }}
        </span>
      </div>

      <TransitionGroup tag="ol" name="list" class="timeline relative m-0 mt-[18px] list-none p-0">
        <li v-for="(enc, i) in [...term.encounters].reverse()" :key="enc.id" class="tl-item">
          <div class="tl-date num">
            {{ dayLabel(enc.captured_at) }}<br /><span class="text-ink-35">{{
              timeLabel(enc.captured_at)
            }}</span>
          </div>
          <span class="tl-dot" :class="i === 0 ? 'tl-dot-now' : ''" />
          <div class="flex flex-col gap-4 md:flex-row md:gap-5">
            <img
              v-if="enc.screenshot_path"
              :src="mediaUrl(enc.screenshot_path)"
              class="plate w-full shrink-0 md:w-[240px]"
              alt="截图"
            />
            <div class="min-w-0">
              <p class="kicker tracking-[0.12em]">
                {{ enc.source_title ?? '未归档' }} · 第 {{ term.encounters.length - i }} 次
              </p>
              <p class="jp mt-1.5 mb-2 text-[19px] leading-[2] md:text-[21px]">
                {{ sentenceParts(enc).before
                }}<b v-if="sentenceParts(enc).target" class="target">{{
                  sentenceParts(enc).target
                }}</b
                >{{ sentenceParts(enc).after }}
              </p>
              <p v-if="enc.contraction_of" class="m-0 text-[12px] text-ink-35">
                缩约形「{{ enc.surface }}」← {{ enc.contraction_of }}
              </p>
              <ExplanationBlock
                v-if="enc.ai_explanation"
                :explanation="enc.ai_explanation"
                :bare="true"
                class="mt-2"
              />
              <button
                class="btn-quiet mt-2"
                :disabled="explaining === enc.id"
                @click="explain(enc, !!enc.ai_explanation)"
              >
                {{
                  explaining === enc.id
                    ? '解释中…'
                    : enc.ai_explanation
                      ? '重新解释'
                      : 'AI 解释这句'
                }}
              </button>
            </div>
          </div>
        </li>
      </TransitionGroup>
    </section>

    <section class="mt-[30px]">
      <p class="kicker mb-3">卡片</p>
      <table v-if="term.cards.length" class="table-plain">
        <TransitionGroup tag="tbody" name="list" class="relative">
          <tr v-for="c in term.cards" :key="c.id">
            <td class="pl-0">{{ CARD_TYPE_LABEL[c.card_type] }}卡</td>
            <td class="num text-ink-50">
              {{ c.due ? `到期 ${humanInterval(c.due)}后` : '新卡'
              }}<template v-if="c.stability"> · 稳定性 {{ c.stability.toFixed(1) }} 天</template>
            </td>
            <td class="pr-0 text-right">
              <span class="seg">
                <button
                  v-for="o in OWNERS"
                  :key="o.value"
                  type="button"
                  class="seg-opt"
                  :aria-pressed="c.review_owner === o.value"
                  @click="setOwner(c, o.value)"
                >
                  {{ o.label }}
                </button>
              </span>
            </td>
          </tr>
        </TransitionGroup>
      </table>
      <p v-else class="m-0 text-[13px] text-ink-35">
        还没有卡片。在收件箱确认这个词时勾选卡片类型。
      </p>
    </section>
  </div>
</template>

<style scoped>
.head-ruby :deep(rt) {
  color: var(--accent);
  font-size: 0.32em;
}
.timeline {
  position: relative;
  padding-left: 22px;
}
.timeline::before {
  content: '';
  position: absolute;
  left: 3px;
  top: 6px;
  bottom: 6px;
  width: 1px;
  background: var(--divider);
}
.tl-item {
  position: relative;
  padding-bottom: 26px;
}
.tl-date {
  font-size: 11px;
  line-height: 1.6;
  color: var(--ink-50);
  margin-bottom: 6px;
}
.tl-dot {
  position: absolute;
  left: -22px;
  top: 6px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  border: 1px solid var(--accent);
  background: var(--bg);
}
.tl-dot-now {
  width: 7px;
  height: 7px;
  left: -23px;
  background: var(--accent);
}
.target {
  font-weight: 600;
  color: var(--gold-deep);
  border-bottom: 2px solid var(--accent);
}
/* 桌面上把日期移到左侧竖线外，成为一条真正的时间轴 */
@media (min-width: 768px) {
  .timeline {
    padding-left: 120px;
  }
  .timeline::before {
    left: 104px;
  }
  .tl-date {
    position: absolute;
    left: -120px;
    top: 2px;
    width: 96px;
    text-align: right;
    margin-bottom: 0;
  }
  .tl-dot {
    left: -20px;
  }
  .tl-dot-now {
    left: -21px;
  }
}
</style>
