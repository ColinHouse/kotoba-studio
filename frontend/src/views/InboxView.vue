<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { DictStatus, Line } from '@/api/types'
import FrequencyOrder from '@/components/inbox/FrequencyOrder.vue'
import InboxLineList from '@/components/inbox/InboxLineList.vue'
import TermEditor, { type ConfirmPayload } from '@/components/inbox/TermEditor.vue'
import TokenChips from '@/components/inbox/TokenChips.vue'
import ExplanationBlock from '@/components/review/ExplanationBlock.vue'
import { useInboxLines, type LineSort, type LineStatus } from '@/composables/useInboxLines'
import { useListKeys } from '@/composables/useListKeys'
import { useTermBuilder } from '@/composables/useTermBuilder'
import { useAppStore } from '@/stores/app'
import { relTime } from '@/utils/format'

const app = useAppStore()
const route = useRoute()
const inbox = useInboxLines()
const {
  analysis,
  picked,
  result: lastResult,
  busy,
  explaining,
  reset,
  analyze,
  confirm,
  explain,
} = useTermBuilder()
const hasFrequencies = ref(false)
/** 手机上列表与整理是同一层级的两屏，返回即回列表。 */
const showDetailOnMobile = ref(false)
const showHelp = ref(false)

/** 键盘：j/k 或 ↑/↓ 移动光标，Enter 打开选中的句子，? 开关帮助。 */
const { cursor } = useListKeys(
  computed(() => inbox.lines.value.length),
  {
    onEnter: (index) => {
      const line = inbox.lines.value[index]
      if (line) selectLine(line)
    },
    onHelp: () => (showHelp.value = !showHelp.value),
  },
)
const cursorId = computed(() => inbox.lines.value[cursor.value]?.id ?? null)
watch(
  () => inbox.selected.value?.id,
  (id) => {
    if (id == null) return
    const index = inbox.lines.value.findIndex((line) => line.id === id)
    if (index >= 0) cursor.value = index
  },
)

const FILTERS: { value: LineStatus; label: string }[] = [
  { value: 'inbox', label: '待整理' },
  { value: 'kept', label: '已确认' },
  { value: 'discarded', label: '已丢弃' },
]

const SORTS: { value: LineSort; label: string }[] = [
  { value: 'recent', label: '最新' },
  { value: 'iplus1', label: 'i+1 优先' },
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
  inbox.selected.value = line
  reset()
  showDetailOnMobile.value = true
  analyze(line)
}

async function confirmTerm(payload: ConfirmPayload) {
  const line = inbox.selected.value
  if (!line) return
  await confirm(line, payload)
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
        <p class="mt-0.5 mb-0 type-note text-ink-50">
          点句子 → 点不认识的词 → 选释义 → 确认建卡。整理放在会后，不打断剧情。 键盘：<kbd
            class="key"
            >j</kbd
          ><kbd class="key">k</kbd> 选句， <kbd class="key">?</kbd> 看全部。
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-3.5">
        <label class="flex flex-col gap-0.5">
          <span class="kicker">会话</span>
          <select
            v-model="inbox.sessionId.value"
            class="num border-0 border-b border-divider bg-transparent pb-[3px] type-note text-ink"
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
        <div class="seg">
          <button
            v-for="s in SORTS"
            :key="s.value"
            type="button"
            class="seg-opt"
            :aria-pressed="inbox.sort.value === s.value"
            :title="s.value === 'iplus1' ? '整句只有一个生词的排最前' : undefined"
            @click="inbox.sort.value = s.value"
          >
            {{ s.label }}
          </button>
        </div>
        <RouterLink v-if="quizSession" :to="`/quiz/${quizSession}`" class="btn btn-primary">
          开始短测
        </RouterLink>
      </div>
    </header>

    <div v-if="showHelp" class="framed mt-4 p-4 type-note leading-[2.1]">
      <div class="flex items-baseline justify-between gap-3">
        <p class="kicker m-0">键盘</p>
        <button class="btn-quiet" @click="showHelp = false">关闭</button>
      </div>
      <p class="m-0 mt-2">
        <kbd class="key">j</kbd><kbd class="key">k</kbd> 或 <kbd class="key">↑</kbd
        ><kbd class="key">↓</kbd> 选句 · <kbd class="key">Enter</kbd> 打开选中的句子
      </p>
      <p class="m-0">
        <kbd class="key">Tab</kbd> 在词之间移动 · <kbd class="key">Enter</kbd> 打开词条编辑器
      </p>
      <p class="m-0">
        <kbd class="key">⌘/Ctrl</kbd>+<kbd class="key">Enter</kbd> 确认建卡 ·
        <kbd class="key">Esc</kbd> 取消
      </p>
      <p class="m-0 text-ink-50">
        输入框里打字时单键不会触发导航；再按 <kbd class="key">?</kbd> 关闭本帮助。
      </p>
    </div>

    <div class="mt-5 md:grid md:grid-cols-[2fr_1px_3fr]">
      <section :class="showDetailOnMobile ? 'hidden md:block' : ''" class="md:pr-[26px]">
        <InboxLineList
          :lines="inbox.lines.value"
          :selected-id="inbox.selected.value?.id ?? null"
          :cursor-id="cursorId"
          :empty-hint="emptyHint"
          @select="selectLine"
        />
        <div class="mt-4 flex items-baseline justify-between gap-3 type-meta">
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

        <p v-if="!inbox.selected.value" class="m-0 py-6 type-note text-ink-35">
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
              v-if="analysis"
              :analysis="analysis"
              :selected-start="picked?.span_start ?? null"
              :legend="true"
              @pick="picked = $event"
            />
            <p v-else class="jp m-0 text-[22px] leading-[2.2]">{{ inbox.selected.value.text }}</p>

            <div v-if="analysis?.contractions.length" class="mt-3.5 flex flex-wrap gap-2">
              <span
                v-for="c in analysis.contractions"
                :key="c.form"
                class="tag tag-fact jp"
                :title="c.note_zh"
                >{{ c.form }} ← {{ c.full }}</span
              >
            </div>

            <FrequencyOrder
              v-if="hasFrequencies && analysis"
              :tokens="analysis.tokens"
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
            <p class="m-0 type-note">
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
