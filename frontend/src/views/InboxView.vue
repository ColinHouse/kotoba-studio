<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { DictStatus, Encounter, Explanation, Line, Term } from '@/api/types'
import FrequencyOrder from '@/components/inbox/FrequencyOrder.vue'
import InboxLineList from '@/components/inbox/InboxLineList.vue'
import TermEditor, { type ConfirmPayload } from '@/components/inbox/TermEditor.vue'
import TokenChips, { type PickedTerm } from '@/components/inbox/TokenChips.vue'
import ExplanationBlock from '@/components/review/ExplanationBlock.vue'
import { useInboxLines, type LineStatus } from '@/composables/useInboxLines'
import { useAppStore } from '@/stores/app'
import { relTime } from '@/utils/format'

const app = useAppStore()
const route = useRoute()
const inbox = useInboxLines()
const picked = ref<PickedTerm | null>(null)
const lastResult = ref<{ term: Term; encounter: Encounter } | null>(null)
const busy = ref(false)
const explaining = ref(false)
const hasFrequencies = ref(false)
/** 手机上列表与整理是同一层级的两屏，返回即回列表。 */
const showDetailOnMobile = ref(false)

const FILTERS: { value: LineStatus; label: string }[] = [
  { value: 'inbox', label: '待整理' },
  { value: 'kept', label: '已确认' },
  { value: 'discarded', label: '已丢弃' },
]

onMounted(async () => {
  api
    .get<DictStatus>('/api/dict/status')
    .then((status) => (hasFrequencies.value = status.has_frequencies))
    .catch(() => undefined)
  try {
    const preferred = typeof route.query.session === 'string' ? route.query.session : null
    await inbox.loadSessions(preferred)
    await inbox.loadLines()
  } catch (e) {
    app.fail(e)
  }
})

function selectLine(line: Line) {
  picked.value = null
  lastResult.value = null
  showDetailOnMobile.value = true
  inbox.select(line)
}

async function confirmTerm(payload: ConfirmPayload) {
  const line = inbox.selected.value
  if (!line) return
  busy.value = true
  try {
    lastResult.value = await api.post<{ term: Term; encounter: Encounter }>('/api/encounters', {
      line_id: line.id,
      ...payload,
    })
    app.toast(
      payload.card_types.length
        ? `已建卡：${lastResult.value.term.headword}`
        : `已记录语境：${lastResult.value.term.headword}`,
      'success',
    )
    line.status = 'kept'
    line.encounter_count += 1
    picked.value = null
    await inbox.analyze(line)
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

async function explain() {
  if (!lastResult.value) return
  explaining.value = true
  try {
    const r = await api.post<{ explanation: Explanation }>('/api/ai/explain', {
      encounter_id: lastResult.value.encounter.id,
    })
    lastResult.value.encounter.ai_explanation = r.explanation
  } catch (e) {
    app.fail(e)
  } finally {
    explaining.value = false
  }
}

const quizSession = computed(() => (inbox.sessionId.value === 'all' ? null : inbox.sessionId.value))
const emptyHint = computed(() =>
  inbox.status.value === 'inbox' ? '这里空空的。去采集页收藏几句台词吧。' : '这里没有句子。',
)
</script>

<template>
  <div>
    <header class="flex flex-wrap items-end justify-between gap-4 border-b border-divider pb-3.5">
      <div>
        <h1 class="page-title text-[27px] md:text-[32px]">收件箱</h1>
        <p class="mt-0.5 mb-0 text-[13px] text-ink-50">
          点句子 → 点不认识的词 → 选释义 → 确认建卡。整理放在会后，不打断剧情。
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-3.5">
        <label class="flex flex-col gap-0.5">
          <span class="kicker">会话</span>
          <select
            v-model="inbox.sessionId.value"
            class="num border-0 border-b border-divider bg-transparent pb-[3px] text-[13px] text-ink"
          >
            <option value="all">全部会话</option>
            <option v-for="s in inbox.sessions.value" :key="s.id" :value="s.id">
              {{ s.source_title ?? '—' }} · {{ relTime(s.started_at) }} · {{ s.line_count }} 句
            </option>
          </select>
        </label>
        <div class="seg">
          <button
            v-for="f in FILTERS"
            :key="f.value"
            type="button"
            class="seg-opt"
            :aria-pressed="inbox.status.value === f.value"
            @click="inbox.status.value = f.value"
          >
            {{ f.label }}
          </button>
        </div>
        <RouterLink v-if="quizSession" :to="`/quiz/${quizSession}`" class="btn btn-primary">
          开始短测
        </RouterLink>
      </div>
    </header>

    <div class="mt-5 md:grid md:grid-cols-[2fr_1px_3fr]">
      <section :class="showDetailOnMobile ? 'hidden md:block' : ''" class="md:pr-[26px]">
        <InboxLineList
          :lines="inbox.lines.value"
          :selected-id="inbox.selected.value?.id ?? null"
          :empty-hint="emptyHint"
          @select="selectLine"
        />
        <div class="mt-4 flex items-baseline justify-between gap-3 text-[12px]">
          <span class="text-ink-35">只有"抬起"的那一条是当前句子</span>
          <button
            v-if="inbox.status.value === 'inbox' && inbox.lines.value.length"
            class="btn-quiet"
            @click="inbox.discardRest"
          >
            丢弃剩余全部
          </button>
        </div>
      </section>

      <div class="hidden bg-divider md:block" />

      <section :class="showDetailOnMobile ? '' : 'hidden md:block'" class="md:pl-[26px]">
        <button
          v-if="inbox.selected.value"
          class="btn-quiet mb-4 md:hidden"
          @click="showDetailOnMobile = false"
        >
          ← 回到列表
        </button>

        <p v-if="!inbox.selected.value" class="m-0 py-6 text-[13px] text-ink-35">
          选择一句台词开始整理。
        </p>

        <template v-else>
          <img
            v-if="inbox.selected.value.screenshot_path"
            :src="mediaUrl(inbox.selected.value.screenshot_path)"
            class="plate w-full rounded-chip"
            alt="这句台词的截图"
          />

          <div class="mt-[22px]">
            <p class="kicker mb-3">分词 · 点一个词开始建卡</p>
            <TokenChips
              v-if="inbox.analysis.value"
              :analysis="inbox.analysis.value"
              :selected-start="picked?.span_start ?? null"
              :legend="true"
              @pick="picked = $event"
            />
            <p v-else class="jp m-0 text-[22px] leading-[2.2]">{{ inbox.selected.value.text }}</p>

            <div
              v-if="inbox.analysis.value?.contractions.length"
              class="mt-3.5 flex flex-wrap gap-2"
            >
              <span
                v-for="c in inbox.analysis.value.contractions"
                :key="c.form"
                class="tag tag-fact jp"
                :title="c.note_zh"
                >{{ c.form }} ← {{ c.full }}</span
              >
            </div>

            <FrequencyOrder
              v-if="hasFrequencies && inbox.analysis.value"
              :tokens="inbox.analysis.value.tokens"
              class="mt-4"
              @pick="picked = $event"
            />

            <div class="mt-4 flex gap-4">
              <button class="btn-quiet" @click="inbox.setStatus(inbox.selected.value, 'discarded')">
                丢弃这句
              </button>
              <button
                v-if="inbox.selected.value.status !== 'kept'"
                class="btn-quiet"
                @click="inbox.setStatus(inbox.selected.value, 'kept')"
              >
                仅保留，不建卡
              </button>
            </div>
          </div>

          <TermEditor
            v-if="picked"
            :picked="picked"
            :busy="busy"
            class="mt-[22px]"
            @confirm="confirmTerm"
            @cancel="picked = null"
          />

          <div v-if="lastResult" class="framed mt-[22px] px-5 py-4">
            <p class="m-0 text-[13px]">
              已记录
              <RouterLink
                :to="`/terms/${lastResult.term.id}`"
                class="jp font-semibold text-accent"
                >{{ lastResult.term.headword }}</RouterLink
              >
              ，第 <span class="num">{{ lastResult.term.encounter_count }}</span> 次遇见
              <span v-if="lastResult.term.trap" class="tag tag-warn ml-2">同形</span>
            </p>
            <ExplanationBlock
              v-if="lastResult.encounter.ai_explanation"
              :explanation="lastResult.encounter.ai_explanation"
              :bare="true"
              class="mt-3"
            />
            <button v-else class="btn-quiet mt-3" :disabled="explaining" @click="explain">
              {{ explaining ? '解释中…' : 'AI 解释这句（可选）' }}
            </button>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>
