<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api, mediaUrl } from '@/api/client'
import type { GameWindow, Line, Region, Session, Source, WindowBinding } from '@/api/types'
import CapturedLines from '@/components/capture/CapturedLines.vue'
import EngineCompare from '@/components/capture/EngineCompare.vue'
import HookStatus from '@/components/capture/HookStatus.vue'
import ManualPaste from '@/components/capture/ManualPaste.vue'
import RegionPicker from '@/components/capture/RegionPicker.vue'
import { useOcrCompare } from '@/composables/useOcrCompare'
import { useScreenCapture } from '@/composables/useScreenCapture'
import { useSessionLines } from '@/composables/useSessionLines'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'
import { fmtDuration } from '@/utils/format'
import { commandKey } from '@/utils/platform'

const app = useAppStore()
const device = useDeviceStore()
const router = useRouter()
const cmdKey = commandKey(navigator.userAgent)

const sources = ref<Source[]>([])
const sourceId = ref<number | null>(null)
const gameWindows = ref<GameWindow[]>([])
const windowsBusy = ref(false)

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
const compare = useOcrCompare()

/** The live window behind the saved binding, so the region can follow it. */
const boundWindow = computed(() => {
  const bound = currentSource.value?.window
  if (!bound) return null
  return gameWindows.value.find((w) => w.process === bound.process) ?? null
})

async function loadWindows() {
  windowsBusy.value = true
  try {
    gameWindows.value = await api.get<GameWindow[]>('/api/capture/windows')
  } catch {
    gameWindows.value = []
  } finally {
    windowsBusy.value = false
  }
}

/** The absolute region the backend will use for this window binding. */
function windowRegion(win: GameWindow, relative: NonNullable<WindowBinding['region']>): Region {
  const [clientLeft, clientTop, clientWidth, clientHeight] = win.client
  if (relative.unit !== 'ratio') {
    // #124 之前存的绑定是像素偏移：照旧读，别把老用户的区域弄乱。
    return {
      left: clientLeft + relative.left,
      top: clientTop + relative.top,
      width: relative.width,
      height: relative.height,
      display: win.display,
    }
  }
  return {
    left: clientLeft + Math.round(relative.left * clientWidth),
    top: clientTop + Math.round(relative.top * clientHeight),
    width: Math.max(1, Math.round(relative.width * clientWidth)),
    height: Math.max(1, Math.round(relative.height * clientHeight)),
    display: win.display,
  }
}

async function pickWindow(event: Event) {
  const handle = Number((event.target as HTMLSelectElement).value)
  const win = gameWindows.value.find((w) => w.handle === handle)
  const source = currentSource.value
  if (!win || !source) return
  try {
    const updated = await api.patch<Source>(`/api/sources/${source.id}`, {
      window: { process: win.process, title: win.title },
    })
    source.window = updated.window
    const relative = updated.window?.region
    if (relative) {
      capture.display.value = win.display
      capture.region.value = windowRegion(win, relative)
    }
    await capture.takeShot()
  } catch (e) {
    app.fail(e)
  }
}

async function clearWindow() {
  const source = currentSource.value
  if (!source) return
  try {
    const updated = await api.patch<Source>(`/api/sources/${source.id}`, { window: null })
    source.window = updated.window
  } catch (e) {
    app.fail(e)
  }
}

async function runCompare() {
  const region = capture.region.value
  if (region) await compare.run(region)
}

async function chooseEngine(name: string) {
  await compare.setDefault(name)
  capture.provider.value = name
}

onMounted(async () => {
  try {
    sources.value = await api.get<Source[]>('/api/sources')
    await app.refreshSettings()
    await capture.init()
    await loadWindows()
    if (session.value) {
      await loadLines()
      const bound = currentSource.value?.window
      const win = bound ? gameWindows.value.find((w) => w.process === bound.process) : undefined
      if (win && bound?.region) {
        // The window may have moved since the region was saved; follow it now.
        capture.display.value = win.display
        capture.region.value = windowRegion(win, bound.region)
      } else {
        capture.region.value = currentSource.value?.region ?? null
      }
      if (!capture.shot.value) await capture.takeShot()
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
    await capture.takeShot()
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
    if (capture.region.value) capture.collect()
  }
}

const framed = computed(() => !!capture.region.value)
const busy = computed(() => capture.busy.value !== '')
const elapsed = computed(() =>
  session.value
    ? fmtDuration(Math.round((Date.now() - new Date(session.value.started_at).getTime()) / 1000))
    : null,
)
</script>

<template>
  <div @keydown="onKey">
    <header class="flex flex-wrap items-center justify-between gap-4 border-b border-divider pb-3">
      <div class="flex items-baseline gap-3">
        <h1 class="page-title text-[26px] md:text-[28px]">采集</h1>
        <span v-if="session" class="inline-flex items-center gap-[7px] type-meta text-ink-70">
          <i class="size-1.5 rounded-full bg-accent" />会话进行中 ·
          {{ currentSource?.title ?? '未指定作品' }}
        </span>
      </div>
      <button v-if="session" class="btn btn-secondary" @click="endSession">结束会话并整理</button>
    </header>

    <p v-if="device.kind !== 'desktop'" class="framed mt-5 p-4 type-note">
      采集需要在运行 ことばこ 的电脑上进行；手机端请使用收件箱与复习。
    </p>

    <HookStatus v-if="device.kind === 'desktop'" />

    <section v-if="!session" class="framed mt-5 flex flex-wrap items-center gap-3 p-4">
      <label class="type-note" for="session-source">先选择作品并开始会话：</label>
      <select id="session-source" v-model="sourceId" class="input w-56">
        <option v-for="s in sources" :key="s.id" :value="s.id">{{ s.title }}</option>
      </select>
      <button class="btn btn-primary" :disabled="!sourceId" @click="startSession">开始会话</button>
      <RouterLink v-if="!sources.length" to="/sources" class="btn-quiet">先添加作品 →</RouterLink>
    </section>

    <template v-else>
      <!-- 一次性设置压成一条线，不和主动作抢注意力 -->
      <div
        class="flex flex-wrap items-center gap-x-[22px] gap-y-2 border-b border-rule py-2.5 type-meta text-ink-70"
      >
        <span class="kicker">一次性设置</span>
        <label class="flex items-center gap-1.5">
          显示器
          <select
            v-model.number="capture.display.value"
            class="num border-0 border-b border-divider bg-transparent type-meta text-ink-70"
          >
            <option v-for="d in capture.displays.value" :key="d.index" :value="d.index">
              {{ d.index + 1 }} · {{ d.width }}×{{ d.height }}
            </option>
          </select>
        </label>
        <label class="flex items-center gap-1.5">
          OCR
          <select
            v-model="capture.provider.value"
            class="border-0 border-b border-divider bg-transparent type-meta text-ink-70"
          >
            <option value="auto">自动</option>
            <option
              v-for="p in capture.providers.value"
              :key="p.name"
              :value="p.name"
              :disabled="!p.available"
            >
              {{ p.name }}{{ p.available ? '' : '（不可用）' }}
            </option>
          </select>
        </label>
        <label class="flex items-center gap-1.5">
          游戏窗口
          <select
            class="max-w-64 border-0 border-b border-divider bg-transparent type-meta text-ink-70"
            :value="boundWindow?.handle ?? ''"
            @change="pickWindow"
          >
            <option value="" disabled>选一个窗口，区域跟着它走</option>
            <option v-for="w in gameWindows" :key="w.handle" :value="w.handle">
              {{ w.process }} · {{ w.title }}（{{ w.width }}×{{ w.height }}）
            </option>
          </select>
        </label>
        <button class="btn-quiet" :disabled="windowsBusy" @click="loadWindows">
          {{ windowsBusy ? '正在枚举…' : '刷新窗口' }}
        </button>
        <button v-if="currentSource?.window" class="btn-quiet" @click="clearWindow">
          取消跟随
        </button>
        <button class="btn-quiet" :disabled="busy" @click="capture.takeShot">重新截取预览</button>
        <ManualPaste @submit="addManual" />
        <span class="ml-auto" :class="framed ? 'text-accent' : 'text-ink-70'">
          {{
            framed
              ? boundWindow
                ? `跟随窗口 ${boundWindow.process}`
                : currentSource?.window
                  ? '窗口不在运行，暂用保存的区域'
                  : `区域已随 ${currentSource?.title ?? '该作品'} 保存`
              : `${currentSource?.title ?? '该作品'} 还没设过对话区域`
          }}
        </span>
      </div>

      <div class="mt-5 md:grid md:grid-cols-[3fr_1px_2fr]">
        <div class="md:pr-[26px]">
          <RegionPicker
            v-if="capture.shot.value"
            v-model="capture.region.value"
            :src="mediaUrl(capture.shot.value.path)!"
            :width="capture.shot.value.width"
            :height="capture.shot.value.height"
            :scale="capture.shot.value.scale"
            :display="capture.display.value"
          />
          <div v-else class="framed grid place-items-center p-10 type-note text-ink-70">
            正在截取屏幕预览…
          </div>

          <div class="mt-2 flex items-baseline justify-between gap-3 type-micro">
            <span v-if="capture.region.value" class="num text-ink-35">
              区域：{{ capture.region.value.left }}, {{ capture.region.value.top }} ·
              {{ capture.region.value.width }}×{{ capture.region.value.height }}（已随作品保存）
            </span>
            <span v-else class="text-accent">未设置区域</span>
            <button v-if="framed" class="btn-quiet" @click="capture.region.value = null">
              重新框选
            </button>
          </div>

          <!-- 整个产品只有一个巨型主操作 -->
          <button
            type="button"
            class="collect mt-[22px]"
            :class="framed ? 'collect-on' : 'collect-off'"
            :disabled="!framed || busy"
            @click="capture.collect"
          >
            <span class="text-left">
              <span class="block font-head text-[32px] leading-none md:text-[38px]">
                {{ capture.busy.value === 'collect' ? '收藏中…' : '收藏这句' }}
              </span>
              <span class="mt-1 block type-meta">
                {{ framed ? '保存台词 + 截图到收件箱，不打断游戏' : '先框选对话框区域才能收藏' }}
              </span>
            </span>
            <span class="hidden items-center gap-2.5 font-head text-[22px] sm:flex">
              <kbd class="key">{{ cmdKey }}</kbd
              ><kbd class="key">↵</kbd>
            </span>
          </button>

          <div class="mt-2.5 flex flex-wrap items-center gap-[18px] type-meta text-ink-70">
            <button class="btn-quiet" :disabled="!framed || busy" @click="capture.runOcr">
              {{ capture.busy.value === 'ocr' ? '识别中…' : '只识别，不保存' }}
            </button>
            <span class="text-ink-35">按一次就回游戏；识别结果在右边核对。</span>
          </div>
        </div>

        <div class="hidden bg-divider md:block" />

        <div class="mt-6 flex flex-col md:mt-0 md:pl-[26px]">
          <template v-if="capture.ocr.value">
            <p class="kicker">
              识别结果 · {{ capture.ocr.value.provider }} ·
              <span class="num">{{ capture.ocr.value.elapsed_ms }} ms</span>
            </p>
            <p class="jp mt-2 mb-0 text-[18px] leading-[1.95] md:text-[20px]">
              {{ capture.ocr.value.normalized ?? capture.ocr.value.text }}
            </p>
            <div class="my-4 h-px bg-divider" />
          </template>

          <CapturedLines
            :lines="lines"
            :elapsed="elapsed"
            :inbox-link="session ? `/inbox?session=${session.id}` : '/inbox'"
            class="flex-1"
          />
        </div>
      </div>

      <Transition name="rise">
        <EngineCompare
          :results="compare.results.value"
          :current="app.settings?.ocr_provider ?? 'auto'"
          :running="compare.running.value"
          :can-run="framed"
          @run="runCompare"
          @select="chooseEngine"
        />
      </Transition>
    </template>
  </div>
</template>

<style scoped>
.collect {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  border-radius: var(--radius-ui);
  padding: 22px 26px;
  text-align: left;
  cursor: pointer;
}
.collect-on {
  border: 2px solid var(--accent);
  background: var(--accent-100);
  color: var(--gold-deep);
}
.collect-on:hover:not(:disabled) {
  background: var(--accent-200);
}
.collect-off {
  border: 1px dashed var(--divider);
  background: transparent;
  color: var(--ink-35);
  cursor: not-allowed;
}
.collect:disabled {
  cursor: not-allowed;
}
.key {
  border: 1px solid currentColor;
  border-radius: 3px;
  padding: 4px 12px;
  font-family: var(--font-head);
  opacity: 0.55;
}
</style>
