<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Coverage, Kind, Session, Source } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'
import { coverageInk, coveragePercent } from '@/utils/coverage'
import { KIND_LABEL } from '@/utils/format'

const app = useAppStore()
const device = useDeviceStore()
const router = useRouter()
const sources = ref<Source[]>([])
const form = ref<{ title: string; title_ja: string; kind: Kind }>({
  title: '',
  title_ja: '',
  kind: 'game',
})
const busy = ref(false)
const coverageId = ref<number | null>(null)
const coverage = ref<Coverage | null>(null)
const coverageBusy = ref(false)
const prestudyLimit = ref(100)
const prestudyBusy = ref(false)

async function runPrestudy(s: Source) {
  prestudyBusy.value = true
  try {
    const r = await api.post<{ created: number; skipped: number }>(
      `/api/sources/${s.id}/prestudy`,
      { limit: prestudyLimit.value },
    )
    app.toast(`已加入 ${r.created} 张，跳过 ${r.skipped} 张`, 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    prestudyBusy.value = false
  }
}

async function showCoverage(s: Source) {
  if (coverageId.value === s.id) {
    coverageId.value = null
    return
  }
  coverageId.value = s.id
  coverage.value = null
  coverageBusy.value = true
  try {
    coverage.value = await api.get<Coverage>(`/api/sources/${s.id}/coverage`)
  } catch (e) {
    coverageId.value = null
    app.fail(e)
  } finally {
    coverageBusy.value = false
  }
}

async function load() {
  sources.value = await api.get<Source[]>('/api/sources')
}
onMounted(() => load().catch(app.fail))

async function create() {
  if (!form.value.title.trim()) return
  busy.value = true
  try {
    await api.post('/api/sources', {
      title: form.value.title.trim(),
      title_ja: form.value.title_ja.trim() || null,
      kind: form.value.kind,
    })
    form.value = { title: '', title_ja: '', kind: 'game' }
    await load()
    app.toast('已添加作品', 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

async function start(s: Source) {
  try {
    app.activeSession = await api.post<Session>('/api/sessions', {
      source_id: s.id,
      mode: 'companion',
    })
    router.push(device.kind === 'desktop' ? '/capture' : '/inbox')
  } catch (e) {
    app.fail(e)
  }
}

async function remove(s: Source) {
  if (!window.confirm(`删除「${s.title}」？句子会保留但不再关联作品。`)) return
  try {
    await api.del(`/api/sources/${s.id}`)
    await load()
  } catch (e) {
    app.fail(e)
  }
}
</script>

<template>
  <div>
    <header class="border-b border-divider pb-3.5">
      <h1 class="page-title text-[27px] md:text-[32px]">作品</h1>
      <p class="mt-0.5 mb-0 text-[13px] text-ink-50">
        词卡按作品归档，并记录同一个词在不同作品里的出现。
      </p>
    </header>

    <form class="mt-5 grid gap-2.5 sm:grid-cols-[1fr_1fr_auto_auto]" @submit.prevent="create">
      <div>
        <label class="field-label" for="src-title">作品名</label>
        <input
          id="src-title"
          v-model="form.title"
          class="input"
          placeholder="中文或任意"
          required
        />
      </div>
      <div>
        <label class="field-label" for="src-title-ja">日文原名（可选）</label>
        <input id="src-title-ja" v-model="form.title_ja" class="input jp" />
      </div>
      <div>
        <label class="field-label" for="src-kind">类型</label>
        <select id="src-kind" v-model="form.kind" class="input">
          <option v-for="(label, k) in KIND_LABEL" :key="k" :value="k">{{ label }}</option>
        </select>
      </div>
      <button class="btn btn-primary self-end" :disabled="busy">添加</button>
    </form>

    <TransitionGroup tag="ul" name="list" class="relative m-0 mt-6 flex list-none flex-col p-0">
      <li v-for="s in sources" :key="s.id" class="border-b border-rule py-3.5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="min-w-0">
            <p class="m-0 font-head text-[19px]">
              {{ s.title }}
              <span v-if="s.title_ja" class="jp text-[13px] font-normal text-ink-35">{{
                s.title_ja
              }}</span>
            </p>
            <p class="num m-0 text-[11px] text-ink-35">
              {{ KIND_LABEL[s.kind] }} · {{ s.line_count }} 句 · 已掌握 {{ s.known_term_count }} /
              {{ s.term_count }} 词 ·
              {{ s.region ? `对话区域 ${s.region.width}×${s.region.height}` : '未设置对话区域' }}
            </p>
          </div>
          <div class="flex shrink-0 items-center gap-3">
            <button v-if="device.kind === 'desktop'" class="btn btn-primary" @click="start(s)">
              开始会话
            </button>
            <button class="btn btn-secondary" @click="showCoverage(s)">覆盖率</button>
            <RouterLink :to="`/library?source=${s.id}`" class="btn btn-secondary">词库</RouterLink>
            <button class="btn-quiet" @click="remove(s)">删除</button>
          </div>
        </div>

        <Transition name="rise">
          <div v-if="coverageId === s.id" class="framed mt-3 p-4">
            <p v-if="coverageBusy || !coverage" class="m-0 text-[13px] text-ink-50">正在统计…</p>
            <template v-else>
              <p class="kicker m-0">覆盖率 · 按出现次数</p>
              <div class="mt-1.5 flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <span
                  class="font-head text-[30px] leading-none"
                  :class="coverageInk(coverage.coverage)"
                >
                  {{ coveragePercent(coverage.coverage) }}
                </span>
                <span class="num text-[12px] text-ink-50">
                  {{ coverage.known_tokens }} / {{ coverage.total_tokens }} 次遇见已掌握 · 词种
                  {{ coveragePercent(coverage.distinct_coverage) }}（{{ coverage.known_terms }} /
                  {{ coverage.distinct_terms }}）
                </span>
              </div>
              <div class="mt-2.5 h-[3px] w-full bg-rule">
                <div class="h-full bg-ink" :style="{ width: coveragePercent(coverage.coverage) }" />
              </div>

              <p v-if="coverage.unknown_top.length" class="kicker mt-4 mb-1.5">最值得先学</p>
              <div v-if="coverage.unknown_top.length" class="flex flex-wrap gap-x-4 gap-y-2">
                <RouterLink
                  v-for="w in coverage.unknown_top"
                  :key="w.term_id"
                  :to="`/terms/${w.term_id}`"
                  class="flex items-center gap-1.5 no-underline"
                >
                  <span class="jp text-[15px] text-ink">{{ w.headword }}</span>
                  <span class="num text-[11px] text-ink-35">×{{ w.count }}</span>
                </RouterLink>
              </div>
              <p v-else class="mt-3 mb-0 text-[13px] text-ink-35">这个作品暂时没有未学的词。</p>

              <div
                v-if="coverage.unknown_top.length"
                class="mt-4 flex flex-wrap items-center gap-3"
              >
                <label class="field-label m-0" :for="`prestudy-limit-${s.id}`">预习卡数量</label>
                <input
                  :id="`prestudy-limit-${s.id}`"
                  v-model.number="prestudyLimit"
                  type="number"
                  min="1"
                  max="500"
                  class="input w-24"
                />
                <button class="btn btn-primary" :disabled="prestudyBusy" @click="runPrestudy(s)">
                  {{ prestudyBusy ? '建卡中…' : '把这些做成预习卡' }}
                </button>
              </div>

              <p v-if="!coverage.has_frequency" class="mt-3 mb-0 text-[11px] text-ink-35">
                未导入频率词典，生词按出现次数排序；导入后按常见度排序。
              </p>
            </template>
          </div>
        </Transition>
      </li>
    </TransitionGroup>
    <p v-if="!sources.length" class="py-4 text-[13px] text-ink-50">
      添加你正在玩的 Galgame 或在看的动画，然后开始第一次会话。
    </p>
  </div>
</template>
