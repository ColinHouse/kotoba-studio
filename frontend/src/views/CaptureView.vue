<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api, mediaUrl, wsUrl } from '@/api/client'
import type { CollectResult, Display, Line, OcrResult, Provider, Region, Screenshot, Session, Source } from '@/api/types'
import RegionPicker from '@/components/RegionPicker.vue'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'
import { relTime } from '@/utils/format'

const app = useAppStore()
const device = useDeviceStore()
const router = useRouter()

const displays = ref<Display[]>([])
const display = ref(0)
const providers = ref<Provider[]>([])
const provider = ref('auto')
const shot = ref<Screenshot | null>(null)
const region = ref<Region | null>(null)
const sources = ref<Source[]>([])
const sourceId = ref<number | null>(null)
const ocr = ref<OcrResult | null>(null)
const lines = ref<Line[]>([])
const manual = ref('')
const busy = ref<'' | 'shot' | 'ocr' | 'collect'>('')
let ws: WebSocket | null = null
let saveTimer: number | undefined

const session = computed(() => app.activeSession)
const currentSource = computed(() => sources.value.find((s) => s.id === session.value?.source_id) ?? null)

async function boot() {
  try {
    ;[displays.value, providers.value, sources.value] = await Promise.all([
      api.get<Display[]>('/api/capture/displays').catch(() => []),
      api.get<Provider[]>('/api/capture/providers'),
      api.get<Source[]>('/api/sources'),
    ])
    await app.refreshSettings()
    provider.value = app.settings?.ocr_provider ?? 'auto'
    if (session.value) {
      lines.value = await api.get<Line[]>(`/api/lines?session_id=${session.value.id}&limit=100`)
      region.value = currentSource.value?.region ?? null
    }
    sourceId.value = session.value?.source_id ?? sources.value[0]?.id ?? null
  } catch (e) {
    app.fail(e)
  }
  connectWs()
}

function upsertLine(line: Line) {
  const idx = lines.value.findIndex((l) => l.id === line.id)
  if (idx >= 0) lines.value[idx] = line
  else lines.value.unshift(line)
}

function connectWs() {
  try {
    ws = new WebSocket(wsUrl('/ws/events'))
    ws.onmessage = (ev) => {
      const event = JSON.parse(ev.data) as { type: string; line: Line }
      if (!session.value || event.line.session_id !== session.value.id) return
      upsertLine(event.line)
    }
  } catch {
    ws = null
  }
}

onMounted(boot)
onBeforeUnmount(() => ws?.close())

async function startSession() {
  if (!sourceId.value) return
  try {
    app.activeSession = await api.post<Session>('/api/sessions', { source_id: sourceId.value, mode: 'companion' })
    lines.value = []
    region.value = currentSource.value?.region ?? null
  } catch (e) {
    app.fail(e)
  }
}

async function endSession() {
  if (!session.value) return
  const id = session.value.id
  try {
    await api.post(`/api/sessions/${id}/end`)
    app.activeSession = null
    router.push(`/inbox?session=${id}`)
  } catch (e) {
    app.fail(e)
  }
}

async function takeShot() {
  busy.value = 'shot'
  try {
    shot.value = await api.post<Screenshot>('/api/capture/screenshot', { display: display.value })
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = ''
  }
}

watch(region, (r) => {
  if (!r || !currentSource.value) return
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(async () => {
    try {
      await api.patch(`/api/sources/${currentSource.value!.id}`, { region: r })
      const s = sources.value.find((x) => x.id === currentSource.value!.id)
      if (s) s.region = r
    } catch (e) {
      app.fail(e)
    }
  }, 400)
})

async function runOcr() {
  if (!region.value) return
  busy.value = 'ocr'
  try {
    ocr.value = await api.post<OcrResult>('/api/capture/ocr', { region: region.value, provider: provider.value === 'auto' ? null : provider.value })
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = ''
  }
}

async function collect() {
  if (!region.value) return
  busy.value = 'collect'
  try {
    const r = await api.post<CollectResult>('/api/capture/collect', { region: region.value, session_id: session.value?.id ?? null, provider: provider.value === 'auto' ? null : provider.value })
    ocr.value = r.ocr
    if (!r.line) app.toast('没有识别到文字', 'error')
    else if (r.duplicate) app.toast('这句已经收藏过了')
    else app.toast('已收藏', 'success')
    if (r.line) upsertLine(r.line)
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = ''
  }
}

async function addManual() {
  const text = manual.value.trim()
  if (!text) return
  try {
    const r = await api.post<{ line: Line; duplicate: boolean }>('/api/lines', { session_id: session.value?.id ?? null, source_id: sourceId.value, text, origin: 'manual' })
    manual.value = ''
    if (r.duplicate) app.toast('这句已经收藏过了')
    upsertLine(r.line)
  } catch (e) {
    app.fail(e)
  }
}

function onKey(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault()
    collect()
  }
}
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-5" @keydown="onKey">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">采集</h1>
        <p class="text-sm text-ink-2">框选一次对话框区域，之后按「收藏这句」（Ctrl/⌘ + Enter）即可保存台词 + 截图。</p>
      </div>
      <div v-if="session" class="flex items-center gap-2 text-sm">
        <span class="chip bg-matcha/15 text-matcha">会话进行中 · {{ currentSource?.title ?? '未指定作品' }}</span>
        <button class="btn-outline" @click="endSession">结束会话并整理</button>
      </div>
    </header>

    <div v-if="device.kind !== 'desktop'" class="card p-4 text-sm">采集需要在运行 Kotoba Studio 的电脑上进行；手机端请使用收件箱与复习。</div>

    <section v-if="!session" class="card flex flex-wrap items-center gap-2 p-4">
      <span class="text-sm">先选择作品并开始会话：</span>
      <select v-model="sourceId" class="input w-56">
        <option v-for="s in sources" :key="s.id" :value="s.id">{{ s.title }}</option>
      </select>
      <button class="btn-primary" :disabled="!sourceId" @click="startSession">开始会话</button>
      <RouterLink v-if="!sources.length" to="/sources" class="text-sm text-accent-2">先添加作品 →</RouterLink>
    </section>

    <div class="grid gap-5 lg:grid-cols-[3fr_2fr]">
      <section class="space-y-3">
        <div class="flex flex-wrap items-center gap-2">
          <select v-model.number="display" class="input w-auto">
            <option v-for="d in displays" :key="d.index" :value="d.index">显示器 {{ d.index + 1 }} · {{ d.width }}×{{ d.height }}</option>
          </select>
          <button class="btn-outline" :disabled="busy === 'shot'" @click="takeShot">{{ busy === 'shot' ? '截取中…' : shot ? '重新截取预览' : '截取屏幕预览' }}</button>
          <select v-model="provider" class="input w-auto" title="OCR 引擎">
            <option value="auto">OCR：自动</option>
            <option v-for="p in providers" :key="p.name" :value="p.name" :disabled="!p.available">{{ p.name }}{{ p.available ? '' : '（不可用）' }}</option>
          </select>
        </div>
        <RegionPicker v-if="shot" v-model="region" :src="mediaUrl(shot.path)!" :width="shot.width" :height="shot.height" :scale="shot.scale" :display="display" />
        <div v-else class="card grid place-items-center p-10 text-sm text-ink-2">先截取一张屏幕预览，然后在预览上框选游戏的对话框区域。</div>
        <p v-if="region" class="text-xs text-ink-3">区域：{{ region.left }}, {{ region.top }} · {{ region.width }}×{{ region.height }}（已随作品保存）</p>

        <div class="flex flex-wrap gap-2">
          <button class="btn-outline" :disabled="!region || busy !== ''" @click="runOcr">{{ busy === 'ocr' ? '识别中…' : '只识别，不保存' }}</button>
          <button class="btn-primary" :disabled="!region || busy !== ''" @click="collect">{{ busy === 'collect' ? '收藏中…' : '收藏这句（⌘/Ctrl+Enter）' }}</button>
        </div>
        <div v-if="ocr" class="card p-3 text-sm">
          <p class="label">识别结果 · {{ ocr.provider }} · {{ ocr.elapsed_ms }} ms</p>
          <p class="jp mt-1 whitespace-pre-wrap text-base">{{ ocr.normalized ?? ocr.text }}</p>
        </div>

        <div class="card p-3">
          <p class="label">手动粘贴（来自 Textractor / 剪贴板）</p>
          <div class="mt-1 flex gap-2">
            <textarea v-model="manual" class="input jp h-20" placeholder="把台词粘贴到这里，Enter 保存" @keydown.enter.exact.prevent="addManual" />
            <button class="btn-outline self-end" :disabled="!manual.trim()" @click="addManual">保存</button>
          </div>
          <p class="mt-1 text-xs text-ink-3">Hook 工具可直接连接 WebSocket <code>{{ wsUrl('/ws/hook') }}</code>，发送纯文本或 {"text": "…"}。</p>
        </div>
      </section>

      <section class="space-y-2">
        <h2 class="font-semibold">本次收藏 <span class="text-sm font-normal text-ink-3">{{ lines.length }} 句</span></h2>
        <ul class="space-y-2">
          <li v-for="l in lines" :key="l.id" class="card flex gap-3 p-3">
            <img v-if="l.screenshot_path" :src="mediaUrl(l.screenshot_path)" class="h-14 w-24 shrink-0 rounded-lg border border-line object-cover" alt="" />
            <div class="min-w-0 flex-1">
              <p class="jp leading-relaxed">{{ l.text }}</p>
              <p class="text-xs text-ink-3">{{ l.origin }} · {{ relTime(l.captured_at) }} · {{ l.status === 'kept' ? '已确认' : l.status === 'discarded' ? '已丢弃' : '待整理' }}</p>
            </div>
          </li>
        </ul>
        <p v-if="!lines.length" class="text-sm text-ink-2">收藏的句子会出现在这里；游戏结束后到收件箱统一整理。</p>
        <RouterLink v-if="lines.length" :to="session ? `/inbox?session=${session.id}` : '/inbox'" class="btn-outline">去收件箱整理 →</RouterLink>
      </section>
    </div>
  </div>
</template>
