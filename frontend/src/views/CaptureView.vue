<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { Line, Region, Session, Source } from '@/api/types'
import CapturedLines from '@/components/capture/CapturedLines.vue'
import ManualPaste from '@/components/capture/ManualPaste.vue'
import RegionPicker from '@/components/capture/RegionPicker.vue'
import { useScreenCapture } from '@/composables/useScreenCapture'
import { useSessionLines } from '@/composables/useSessionLines'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'

const app = useAppStore()
const device = useDeviceStore()
const router = useRouter()

const sources = ref<Source[]>([])
const sourceId = ref<number | null>(null)

const session = computed(() => app.activeSession)
const sessionId = computed(() => session.value?.id ?? null)
const currentSource = computed(
  () => sources.value.find((s) => s.id === session.value?.source_id) ?? null,
)

const { lines, upsert, load: loadLines, connect } = useSessionLines(sessionId)

async function persistRegion(region: Region) {
  const source = currentSource.value
  if (!source) return
  await api.patch(`/api/sources/${source.id}`, { region })
  source.region = region
}

const capture = useScreenCapture({ sessionId, persistRegion, onLine: upsert })

onMounted(async () => {
  try {
    sources.value = await api.get<Source[]>('/api/sources')
    await app.refreshSettings()
    await capture.init()
    if (session.value) {
      await loadLines()
      capture.region.value = currentSource.value?.region ?? null
    }
    sourceId.value = session.value?.source_id ?? sources.value[0]?.id ?? null
  } catch (e) {
    app.fail(e)
  }
  connect()
})

async function startSession() {
  if (!sourceId.value) return
  try {
    app.activeSession = await api.post<Session>('/api/sessions', {
      source_id: sourceId.value,
      mode: 'companion',
    })
    lines.value = []
    capture.region.value = currentSource.value?.region ?? null
  } catch (e) {
    app.fail(e)
  }
}

async function endSession() {
  const id = sessionId.value
  if (id == null) return
  try {
    await api.post(`/api/sessions/${id}/end`)
    app.activeSession = null
    router.push(`/inbox?session=${id}`)
  } catch (e) {
    app.fail(e)
  }
}

async function addManual(text: string) {
  try {
    const result = await api.post<{ line: Line; duplicate: boolean }>('/api/lines', {
      session_id: sessionId.value,
      source_id: sourceId.value,
      text,
      origin: 'manual',
    })
    if (result.duplicate) app.toast('这句已经收藏过了')
    upsert(result.line)
  } catch (e) {
    app.fail(e)
  }
}

function onKey(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
    event.preventDefault()
    capture.collect()
  }
}
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-5" @keydown="onKey">
    <header class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">采集</h1>
        <p class="text-sm text-ink-2">
          框选一次对话框区域，之后按「收藏这句」（Ctrl/⌘ + Enter）即可保存台词 + 截图。
        </p>
      </div>
      <div v-if="session" class="flex items-center gap-2 text-sm">
        <span class="chip bg-matcha/15 text-matcha">
          会话进行中 · {{ currentSource?.title ?? '未指定作品' }}
        </span>
        <button class="btn-outline" @click="endSession">结束会话并整理</button>
      </div>
    </header>

    <div v-if="device.kind !== 'desktop'" class="card p-4 text-sm">
      采集需要在运行 Kotoba Studio 的电脑上进行；手机端请使用收件箱与复习。
    </div>

    <section v-if="!session" class="card flex flex-wrap items-center gap-2 p-4">
      <label class="text-sm" for="session-source">先选择作品并开始会话：</label>
      <select id="session-source" v-model="sourceId" class="input w-56">
        <option v-for="s in sources" :key="s.id" :value="s.id">{{ s.title }}</option>
      </select>
      <button class="btn-primary" :disabled="!sourceId" @click="startSession">开始会话</button>
      <RouterLink v-if="!sources.length" to="/sources" class="text-sm text-accent-2">
        先添加作品 →
      </RouterLink>
    </section>

    <div class="grid gap-5 lg:grid-cols-[3fr_2fr]">
      <section class="space-y-3">
        <div class="flex flex-wrap items-center gap-2">
          <select v-model.number="capture.display.value" class="input w-auto" aria-label="显示器">
            <option v-for="d in capture.displays.value" :key="d.index" :value="d.index">
              显示器 {{ d.index + 1 }} · {{ d.width }}×{{ d.height }}
            </option>
          </select>
          <button
            class="btn-outline"
            :disabled="capture.busy.value === 'shot'"
            @click="capture.takeShot"
          >
            {{
              capture.busy.value === 'shot'
                ? '截取中…'
                : capture.shot.value
                  ? '重新截取预览'
                  : '截取屏幕预览'
            }}
          </button>
          <select v-model="capture.provider.value" class="input w-auto" aria-label="OCR 引擎">
            <option value="auto">OCR：自动</option>
            <option
              v-for="p in capture.providers.value"
              :key="p.name"
              :value="p.name"
              :disabled="!p.available"
            >
              {{ p.name }}{{ p.available ? '' : '（不可用）' }}
            </option>
          </select>
        </div>

        <RegionPicker
          v-if="capture.shot.value"
          v-model="capture.region.value"
          :src="mediaUrl(capture.shot.value.path)!"
          :width="capture.shot.value.width"
          :height="capture.shot.value.height"
          :scale="capture.shot.value.scale"
          :display="capture.display.value"
        />
        <div v-else class="card grid place-items-center p-10 text-sm text-ink-2">
          先截取一张屏幕预览，然后在预览上框选游戏的对话框区域。
        </div>
        <p v-if="capture.region.value" class="text-xs text-ink-3">
          区域：{{ capture.region.value.left }}, {{ capture.region.value.top }} ·
          {{ capture.region.value.width }}×{{ capture.region.value.height }}（已随作品保存）
        </p>

        <div class="flex flex-wrap gap-2">
          <button
            class="btn-outline"
            :disabled="!capture.region.value || capture.busy.value !== ''"
            @click="capture.runOcr"
          >
            {{ capture.busy.value === 'ocr' ? '识别中…' : '只识别，不保存' }}
          </button>
          <button
            class="btn-primary"
            :disabled="!capture.region.value || capture.busy.value !== ''"
            @click="capture.collect"
          >
            {{ capture.busy.value === 'collect' ? '收藏中…' : '收藏这句（⌘/Ctrl+Enter）' }}
          </button>
        </div>

        <div v-if="capture.ocr.value" class="card p-3 text-sm">
          <p class="label">
            识别结果 · {{ capture.ocr.value.provider }} · {{ capture.ocr.value.elapsed_ms }} ms
          </p>
          <p class="jp mt-1 whitespace-pre-wrap text-base">
            {{ capture.ocr.value.normalized ?? capture.ocr.value.text }}
          </p>
        </div>

        <ManualPaste @submit="addManual" />
      </section>

      <CapturedLines
        :lines="lines"
        :inbox-link="session ? `/inbox?session=${session.id}` : '/inbox'"
      />
    </div>
  </div>
</template>
