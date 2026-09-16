<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { QuizItem, SessionSummary } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'
import { diffAnswer } from '@/utils/diff'
import { fmtDuration } from '@/utils/format'

const props = defineProps<{ sessionId: string }>()
const app = useAppStore()
const device = useDeviceStore()
const items = ref<QuizItem[]>([])
const index = ref(0)
const given = ref('')
const revealed = ref(false)
const result = ref<{ correct: boolean; expected: string } | null>(null)
const score = ref({ answered: 0, correct: 0 })
const summary = ref<SessionSummary | null>(null)
const loading = ref(true)
const startedAt = ref(Date.now())
const input = ref<HTMLInputElement | null>(null)

const current = computed(() => items.value[index.value] ?? null)
const pieces = computed(() => (result.value && given.value ? diffAnswer(given.value, result.value.expected) : []))

onMounted(async () => {
  try {
    const r = await api.post<{ items: QuizItem[] }>(`/api/quiz/sessions/${props.sessionId}?limit=12`)
    items.value = r.items
    if (!r.items.length) summary.value = await api.get<SessionSummary>(`/api/sessions/${props.sessionId}/summary`)
  } catch (e) {
    app.fail(e)
  } finally {
    loading.value = false
  }
})

async function submit(selfCorrect?: boolean) {
  if (!current.value) return
  const item = current.value
  try {
    const r = await api.post<{ correct: boolean; expected: string }>('/api/quiz/answers', {
      card_id: item.card_id,
      encounter_id: item.encounter_id,
      kind: item.kind,
      given: item.kind === 'meaning' ? null : given.value,
      correct: item.kind === 'meaning' ? selfCorrect : null,
      duration_ms: Date.now() - startedAt.value,
      device_id: device.device?.id ?? null,
      session_id: Number(props.sessionId),
    })
    result.value = r
    score.value.answered += 1
    if (r.correct) score.value.correct += 1
  } catch (e) {
    app.fail(e)
  }
}

async function next() {
  index.value += 1
  given.value = ''
  revealed.value = false
  result.value = null
  startedAt.value = Date.now()
  if (!current.value) summary.value = await api.get<SessionSummary>(`/api/sessions/${props.sessionId}/summary`)
  else setTimeout(() => input.value?.focus(), 0)
}
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-4">
    <header class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">会后短测</h1>
      <span class="text-sm text-ink-3">{{ Math.min(index + 1, items.length) }} / {{ items.length }} · 对 {{ score.correct }}</span>
    </header>

    <div v-if="loading" class="card p-8 text-center text-sm text-ink-2">出题中…</div>

    <template v-else-if="current">
      <div class="card space-y-4 p-6">
        <p class="label">{{ { reading: '读音回忆', cloze: '语境填空', meaning: '语境释义', listening: '听音理解' }[current.kind] }}</p>
        <audio v-if="current.kind === 'listening' && current.audio_path" :src="mediaUrl(current.audio_path)" controls />
        <p v-else class="jp text-2xl leading-relaxed">{{ current.prompt }}</p>
        <p class="text-sm text-ink-2">{{ current.hint }}</p>

        <template v-if="current.kind === 'meaning'">
          <div v-if="!revealed"><button class="btn-primary" @click="revealed = true">显示答案</button></div>
          <template v-else-if="!result">
            <p class="text-lg">{{ current.answer }}</p>
            <div class="flex gap-2">
              <button class="btn bg-red-500/90 text-white" @click="submit(false)">没想起来</button>
              <button class="btn bg-matcha text-white" @click="submit(true)">想起来了</button>
            </div>
          </template>
        </template>
        <template v-else>
          <form v-if="!result" class="flex gap-2" @submit.prevent="submit()">
            <input ref="input" v-model="given" class="input jp text-lg" autofocus placeholder="输入答案…" />
            <button class="btn-primary" :disabled="!given.trim()">提交</button>
          </form>
        </template>

        <div v-if="result" class="rounded-xl p-3" :class="result.correct ? 'bg-matcha/10' : 'bg-red-50'">
          <p class="font-semibold" :class="result.correct ? 'text-matcha' : 'text-red-700'">{{ result.correct ? '正确！' : '不对，正确答案：' }}</p>
          <p v-if="!result.correct" class="jp text-xl">
            <template v-if="pieces.length"><span v-for="(p, i) in pieces" :key="i" :class="p.ok ? '' : 'font-bold text-red-700'">{{ p.text }}</span></template>
            <template v-else>{{ result.expected }}</template>
          </p>
          <p class="mt-1 text-sm text-ink-2 jp">{{ current.headword }}（{{ current.reading }}）</p>
          <button class="btn-primary mt-3" @click="next">下一题</button>
        </div>
      </div>
      <p class="text-center text-xs text-ink-3">短测结果只作记录，不改变 FSRS 的正式复习安排。</p>
    </template>

    <div v-else-if="summary" class="card space-y-4 p-6">
      <h2 class="text-lg font-semibold">本次会话复盘</h2>
      <div class="grid grid-cols-2 gap-3 text-center sm:grid-cols-4">
        <div class="rounded-xl bg-paper-2 p-3"><span class="label">收藏</span><p class="text-2xl font-semibold">{{ summary.lines_total }}</p></div>
        <div class="rounded-xl bg-paper-2 p-3"><span class="label">确认</span><p class="text-2xl font-semibold">{{ summary.kept }}</p></div>
        <div class="rounded-xl bg-paper-2 p-3"><span class="label">新词</span><p class="text-2xl font-semibold">{{ summary.new_terms.length }}</p></div>
        <div class="rounded-xl bg-paper-2 p-3"><span class="label">再见词</span><p class="text-2xl font-semibold">{{ summary.seen_again_terms.length }}</p></div>
      </div>
      <p class="text-sm text-ink-2">建卡 {{ summary.cards_created }} 张 · 短测 {{ summary.quiz.correct }}/{{ summary.quiz.answered }} · 时长 {{ fmtDuration(summary.duration_s) }}</p>
      <div v-if="summary.seen_again_terms.length" class="text-sm">
        <span class="label">这些词你之前也遇到过</span>
        <p class="jp">{{ summary.seen_again_terms.map((t) => t.headword).join('、') }}</p>
      </div>
      <div class="flex gap-2">
        <RouterLink :to="`/inbox?session=${sessionId}`" class="btn-outline">回到收件箱</RouterLink>
        <RouterLink to="/review" class="btn-primary">去正式复习</RouterLink>
      </div>
    </div>
  </div>
</template>
