<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { Encounter, Explanation, Line, Term } from '@/api/types'
import InboxLineList from '@/components/inbox/InboxLineList.vue'
import TermEditor, { type ConfirmPayload } from '@/components/inbox/TermEditor.vue'
import TokenChips, { type PickedTerm } from '@/components/inbox/TokenChips.vue'
import ExplanationBlock from '@/components/review/ExplanationBlock.vue'
import { useInboxLines } from '@/composables/useInboxLines'
import { useAppStore } from '@/stores/app'
import { relTime } from '@/utils/format'

const app = useAppStore()
const route = useRoute()
const inbox = useInboxLines()
const picked = ref<PickedTerm | null>(null)
const lastResult = ref<{ term: Term; encounter: Encounter } | null>(null)
const busy = ref(false)
const explaining = ref(false)

onMounted(async () => {
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

const quizSession = computed(() =>
  inbox.sessionId.value === 'all' ? null : inbox.sessionId.value,
)
const emptyHint = computed(() =>
  inbox.status.value === 'inbox' ? '这里空空的。去采集页收藏几句台词吧。' : '这里没有句子。',
)
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-4">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">收件箱</h1>
        <p class="text-sm text-ink-2">
          点句子 → 点不认识的词 → 选释义 → 确认建卡。整理放在会后，不打断剧情。
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <select v-model="inbox.sessionId.value" class="input w-auto" aria-label="会话">
          <option value="all">全部会话</option>
          <option v-for="s in inbox.sessions.value" :key="s.id" :value="s.id">
            {{ s.source_title ?? '—' }} · {{ relTime(s.started_at) }} · {{ s.line_count }} 句
          </option>
        </select>
        <select v-model="inbox.status.value" class="input w-auto" aria-label="状态">
          <option value="inbox">待整理</option>
          <option value="kept">已确认</option>
          <option value="discarded">已丢弃</option>
        </select>
        <RouterLink v-if="quizSession" :to="`/quiz/${quizSession}`" class="btn-primary">
          开始短测
        </RouterLink>
      </div>
    </header>

    <div class="grid gap-4 lg:grid-cols-[2fr_3fr]">
      <section class="space-y-2">
        <InboxLineList
          :lines="inbox.lines.value"
          :selected-id="inbox.selected.value?.id ?? null"
          :empty-hint="emptyHint"
          @select="selectLine"
        />
        <button
          v-if="inbox.status.value === 'inbox' && inbox.lines.value.length"
          class="btn-ghost text-xs text-red-600"
          @click="inbox.discardRest"
        >
          丢弃剩余全部
        </button>
      </section>

      <section class="space-y-3">
        <div v-if="!inbox.selected.value" class="card p-6 text-sm text-ink-2">
          选择一句台词开始整理。
        </div>
        <template v-else>
          <div class="card p-4">
            <img
              v-if="inbox.selected.value.screenshot_path"
              :src="mediaUrl(inbox.selected.value.screenshot_path)"
              class="mb-3 max-h-56 rounded-lg border border-line"
              alt="截图"
            />
            <TokenChips
              v-if="inbox.analysis.value"
              :analysis="inbox.analysis.value"
              :selected-start="picked?.span_start ?? null"
              @pick="picked = $event"
            />
            <p v-else class="jp">{{ inbox.selected.value.text }}</p>
            <div
              v-if="inbox.analysis.value?.contractions.length"
              class="mt-2 flex flex-wrap gap-1 text-xs"
            >
              <span
                v-for="c in inbox.analysis.value.contractions"
                :key="c.form"
                class="chip bg-plum/10 text-plum"
                :title="c.note_zh"
              >
                {{ c.form }} ← {{ c.full }}
              </span>
            </div>
            <div class="mt-3 flex gap-2">
              <button
                class="btn-ghost text-xs"
                @click="inbox.setStatus(inbox.selected.value, 'discarded')"
              >
                丢弃这句
              </button>
              <button
                v-if="inbox.selected.value.status !== 'kept'"
                class="btn-ghost text-xs"
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
            @confirm="confirmTerm"
            @cancel="picked = null"
          />

          <div v-if="lastResult" class="card space-y-2 p-4">
            <p class="text-sm">
              已记录
              <RouterLink
                :to="`/terms/${lastResult.term.id}`"
                class="jp font-semibold text-accent-2"
                >{{ lastResult.term.headword }}</RouterLink
              >，第 {{ lastResult.term.encounter_count }} 次遇见
              <span v-if="lastResult.term.trap" class="chip ml-2 bg-accent/15 text-xs text-accent-2">
                中日同形：日语＝{{ lastResult.term.trap.ja_meaning }}
              </span>
            </p>
            <ExplanationBlock
              v-if="lastResult.encounter.ai_explanation"
              :explanation="lastResult.encounter.ai_explanation"
            />
            <button v-else class="btn-outline text-xs" :disabled="explaining" @click="explain">
              {{ explaining ? '解释中…' : 'AI 解释这句（可选）' }}
            </button>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>
