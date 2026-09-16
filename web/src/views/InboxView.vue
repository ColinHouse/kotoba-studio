<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { Analysis, CardType, DictEntry, Encounter, Explanation, Line, Session, Term } from '@/api/types'
import ExplanationBlock from '@/components/ExplanationBlock.vue'
import TokenChips, { type PickedTerm } from '@/components/TokenChips.vue'
import { headwordFor } from '@/utils/headword'
import { useAppStore } from '@/stores/app'
import { hasKanji } from '@/utils/kana'
import { CARD_TYPE_LABEL, relTime } from '@/utils/format'

const app = useAppStore()
const route = useRoute()
const sessions = ref<Session[]>([])
const sessionId = ref<number | 'all'>('all')
const status = ref<'inbox' | 'kept' | 'discarded'>('inbox')
const lines = ref<Line[]>([])
const selected = ref<Line | null>(null)
const analysis = ref<Analysis | null>(null)
const picked = ref<PickedTerm | null>(null)
const candidate = ref<DictEntry | null>(null)
const glossZh = ref('')
const glossEn = ref('')
const cardTypes = ref<CardType[]>([])
const busy = ref(false)
const lastResult = ref<{ term: Term; encounter: Encounter } | null>(null)
const explaining = ref(false)

async function loadSessions() {
  sessions.value = await api.get<Session[]>('/api/sessions?limit=30')
  const q = route.query.session
  if (typeof q === 'string' && q) sessionId.value = Number(q)
  else if (app.activeSession) sessionId.value = app.activeSession.id
}

async function loadLines() {
  const params = new URLSearchParams({ status: status.value, limit: '200' })
  if (sessionId.value !== 'all') params.set('session_id', String(sessionId.value))
  lines.value = await api.get<Line[]>(`/api/lines?${params}`)
  if (selected.value && !lines.value.some((l) => l.id === selected.value!.id)) selected.value = null
}

onMounted(async () => {
  try {
    await loadSessions()
    await loadLines()
  } catch (e) {
    app.fail(e)
  }
})
watch([sessionId, status], () => loadLines().catch(app.fail))

async function select(line: Line) {
  selected.value = line
  analysis.value = null
  picked.value = null
  lastResult.value = null
  try {
    analysis.value = await api.post<Analysis>(`/api/lines/${line.id}/analyze`)
  } catch (e) {
    app.fail(e)
  }
}

function onPick(p: PickedTerm) {
  picked.value = p
  candidate.value = p.candidates[0] ?? null
  glossEn.value = candidate.value?.senses[0]?.gloss_en.slice(0, 3).join('; ') ?? ''
  glossZh.value = ''
  cardTypes.value = hasKanji(p.headword) ? ['reading', 'cloze'] : ['meaning', 'cloze']
}

function chooseCandidate(c: DictEntry) {
  candidate.value = c
  if (picked.value) {
    picked.value = { ...picked.value, headword: headwordFor(c, picked.value.surface, c.headword), reading: c.reading, pos: c.pos[0] ?? null }
    cardTypes.value = hasKanji(picked.value.headword) ? ['reading', 'cloze'] : ['meaning', 'cloze']
  }
  glossEn.value = c.senses[0]?.gloss_en.slice(0, 3).join('; ') ?? ''
}

const canConfirm = computed(() => !!picked.value && picked.value.headword.trim().length > 0)

async function confirmTerm() {
  if (!picked.value || !selected.value) return
  busy.value = true
  try {
    const r = await api.post<{ term: Term; encounter: Encounter }>('/api/encounters', {
      line_id: selected.value.id,
      headword: picked.value.headword.trim(),
      reading: picked.value.reading.trim(),
      surface: picked.value.surface,
      span_start: picked.value.span_start,
      span_end: picked.value.span_end,
      pos: picked.value.pos,
      jmdict_id: candidate.value?.id ?? null,
      sense: glossZh.value.trim() || glossEn.value.trim() ? { gloss_zh: glossZh.value.trim() || null, gloss_en: glossEn.value.trim() || null, origin: glossZh.value.trim() ? 'user' : 'jmdict' } : null,
      card_types: cardTypes.value,
    })
    lastResult.value = r
    app.toast(cardTypes.value.length ? `已建卡：${r.term.headword}` : `已记录语境：${r.term.headword}`, 'success')
    selected.value.status = 'kept'
    selected.value.encounter_count += 1
    analysis.value = await api.post<Analysis>(`/api/lines/${selected.value.id}/analyze`)
    picked.value = null
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

async function setStatus(line: Line, s: 'inbox' | 'kept' | 'discarded') {
  try {
    const updated = await api.patch<Line>(`/api/lines/${line.id}`, { status: s })
    Object.assign(line, updated)
    if (s !== status.value) lines.value = lines.value.filter((l) => l.id !== line.id)
    if (selected.value?.id === line.id && s !== status.value) selected.value = null
  } catch (e) {
    app.fail(e)
  }
}

async function discardRest() {
  if (!window.confirm(`把剩余 ${lines.value.length} 句全部标记为丢弃？`)) return
  for (const l of [...lines.value]) await setStatus(l, 'discarded')
}

async function explain() {
  if (!lastResult.value) return
  explaining.value = true
  try {
    const r = await api.post<{ explanation: Explanation }>('/api/ai/explain', { encounter_id: lastResult.value.encounter.id })
    lastResult.value.encounter.ai_explanation = r.explanation
  } catch (e) {
    app.fail(e)
  } finally {
    explaining.value = false
  }
}

const quizSession = computed(() => (sessionId.value === 'all' ? null : sessionId.value))
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-4">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">收件箱</h1>
        <p class="text-sm text-ink-2">点句子 → 点不认识的词 → 选释义 → 确认建卡。整理放在会后，不打断剧情。</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <select v-model="sessionId" class="input w-auto">
          <option value="all">全部会话</option>
          <option v-for="s in sessions" :key="s.id" :value="s.id">{{ s.source_title ?? '—' }} · {{ relTime(s.started_at) }} · {{ s.line_count }} 句</option>
        </select>
        <select v-model="status" class="input w-auto">
          <option value="inbox">待整理</option>
          <option value="kept">已确认</option>
          <option value="discarded">已丢弃</option>
        </select>
        <RouterLink v-if="quizSession" :to="`/quiz/${quizSession}`" class="btn-primary">开始短测</RouterLink>
      </div>
    </header>

    <div class="grid gap-4 lg:grid-cols-[2fr_3fr]">
      <section class="space-y-2">
        <ul class="space-y-2">
          <li v-for="l in lines" :key="l.id" class="card cursor-pointer p-3 transition" :class="selected?.id === l.id ? 'border-accent ring-1 ring-accent' : 'hover:border-ink-3'" @click="select(l)">
            <div class="flex gap-3">
              <img v-if="l.screenshot_path" :src="mediaUrl(l.screenshot_path)" class="h-12 w-20 shrink-0 rounded-md border border-line object-cover" alt="" />
              <div class="min-w-0 flex-1">
                <p class="jp leading-relaxed">{{ l.text }}</p>
                <p class="text-xs text-ink-3">{{ relTime(l.captured_at) }}<span v-if="l.encounter_count"> · {{ l.encounter_count }} 个词</span></p>
              </div>
            </div>
          </li>
        </ul>
        <p v-if="!lines.length" class="text-sm text-ink-2">这里空空的。{{ status === 'inbox' ? '去采集页收藏几句台词吧。' : '' }}</p>
        <button v-if="status === 'inbox' && lines.length" class="btn-ghost text-xs text-red-600" @click="discardRest">丢弃剩余全部</button>
      </section>

      <section class="space-y-3">
        <div v-if="!selected" class="card p-6 text-sm text-ink-2">选择左侧的一句台词开始整理。</div>
        <template v-else>
          <div class="card p-4">
            <img v-if="selected.screenshot_path" :src="mediaUrl(selected.screenshot_path)" class="mb-3 max-h-56 rounded-lg border border-line" alt="截图" />
            <TokenChips v-if="analysis" :analysis="analysis" :selected-start="picked?.span_start ?? null" @pick="onPick" />
            <p v-else class="jp">{{ selected.text }}</p>
            <div v-if="analysis?.contractions.length" class="mt-2 flex flex-wrap gap-1 text-xs">
              <span v-for="c in analysis.contractions" :key="c.form" class="chip bg-plum/10 text-plum" :title="c.note_zh">{{ c.form }} ← {{ c.full }}</span>
            </div>
            <div class="mt-3 flex gap-2">
              <button class="btn-ghost text-xs" @click="setStatus(selected, 'discarded')">丢弃这句</button>
              <button v-if="selected.status !== 'kept'" class="btn-ghost text-xs" @click="setStatus(selected, 'kept')">仅保留，不建卡</button>
            </div>
          </div>

          <div v-if="picked" class="card space-y-3 p-4">
            <div class="flex items-center justify-between">
              <p class="jp text-xl font-semibold">{{ picked.surface }} <span class="text-sm font-normal text-ink-3">{{ picked.is_expression ? '表达' : picked.pos ?? '' }}</span></p>
              <span v-if="picked.known_status" class="text-xs text-ink-3">已在词库：{{ picked.known_status }}</span>
            </div>
            <div v-if="picked.candidates.length" class="space-y-1">
              <p class="label">词典候选</p>
              <button v-for="c in picked.candidates" :key="c.id" type="button" class="block w-full rounded-lg border px-3 py-2 text-left text-sm" :class="candidate?.id === c.id ? 'border-accent bg-accent/10' : 'border-line'" @click="chooseCandidate(c)">
                <span class="jp font-semibold">{{ c.headword }}</span> <span class="jp text-ink-2">{{ c.reading }}</span>
                <span v-if="c.common" class="ml-1 chip bg-matcha/15 text-[10px] text-matcha">常用</span>
                <span class="block text-ink-2">{{ c.senses[0]?.gloss_en.slice(0, 3).join('; ') }}</span>
              </button>
            </div>
            <div class="grid gap-2 sm:grid-cols-2">
              <label class="text-sm"><span class="label">词条</span><input v-model="picked.headword" class="input jp" /></label>
              <label class="text-sm"><span class="label">读音</span><input v-model="picked.reading" class="input jp" /></label>
              <label class="text-sm sm:col-span-2"><span class="label">中文释义（这里的意思）</span><input v-model="glossZh" class="input" placeholder="例如：请客、宴请" /></label>
              <label class="text-sm sm:col-span-2"><span class="label">英文释义（词典）</span><input v-model="glossEn" class="input" /></label>
            </div>
            <div class="flex flex-wrap items-center gap-3 text-sm">
              <span class="label">卡片</span>
              <label v-for="t in (['reading', 'meaning', 'cloze'] as CardType[])" :key="t" class="flex items-center gap-1"><input v-model="cardTypes" type="checkbox" :value="t" />{{ CARD_TYPE_LABEL[t] }}</label>
            </div>
            <div class="flex gap-2">
              <button class="btn-primary" :disabled="!canConfirm || busy" @click="confirmTerm">{{ cardTypes.length ? '确认并建卡' : '只记录语境' }}</button>
              <button class="btn-ghost" @click="picked = null">取消</button>
            </div>
          </div>

          <div v-if="lastResult" class="card space-y-2 p-4">
            <p class="text-sm">已记录 <RouterLink :to="`/terms/${lastResult.term.id}`" class="jp font-semibold text-accent-2">{{ lastResult.term.headword }}</RouterLink>，第 {{ lastResult.term.encounter_count }} 次遇见<span v-if="lastResult.term.trap" class="ml-2 chip bg-accent/15 text-xs text-accent-2">中日同形：日语＝{{ lastResult.term.trap.ja_meaning }}</span></p>
            <ExplanationBlock v-if="lastResult.encounter.ai_explanation" :explanation="lastResult.encounter.ai_explanation" />
            <button v-else class="btn-outline text-xs" :disabled="explaining" @click="explain">{{ explaining ? '解释中…' : 'AI 解释这句（可选）' }}</button>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>
