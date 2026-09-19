<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { wsUrl } from '@/api/client'
import { connectHook, disconnectHook, listHooks, probeHook } from '@/api/capture'
import type { HookState, HookStatus } from '@/api/types'
import { t, type MessagePath } from '@/i18n'
import { useAppStore } from '@/stores/app'
import { relSeconds } from '@/utils/format'

const TOOLS = [
  { name: 'textractor', label: 'Textractor' },
  { name: 'agent', label: 'Agent' },
  { name: 'luna', label: 'LunaTranslator' },
]

/** Third-party extension, not bundled: users who reach the failure state need the walkthrough. */
const TEXTTRACTOR_GUIDE = 'https://drinosaret.github.io/vn-club-resources/textractor-guide/'

const STATE_KEY: Record<HookState, MessagePath> = {
  idle: 'capture.hook.state.idle',
  connecting: 'capture.hook.state.connecting',
  connected: 'capture.hook.state.connected',
}

const app = useAppStore()
const tool = ref(TOOLS[0]!.name)
const hooks = ref<HookStatus[]>([])
const busy = ref(false)
const showAdvanced = ref(false)
const urlDraft = ref('')
let poll: number | undefined

const current = computed(() => hooks.value.find((h) => h.name === tool.value) ?? null)
const state = computed<HookState>(() => current.value?.status ?? 'idle')

async function refresh() {
  try {
    hooks.value = await listHooks()
  } catch {
    /* polling retries; the page has its own offline handling */
  }
}

// The draft follows the saved address, but never overwrites what is being typed:
// it only changes when the selected tool or the configured URL does.
watch(
  [tool, () => current.value?.url],
  () => {
    urlDraft.value = current.value?.url ?? ''
  },
  { immediate: true },
)

watch(tool, () => {
  showAdvanced.value = false
})

async function connect(url?: string) {
  busy.value = true
  try {
    await connectHook(tool.value, url)
    await refresh()
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

async function disconnect() {
  busy.value = true
  try {
    await disconnectHook(tool.value)
    await refresh()
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

async function test() {
  busy.value = true
  try {
    const result = await probeHook(tool.value)
    if (result.ok) {
      app.toast(t('capture.hook.testOk'), 'success')
      await connectHook(tool.value)
    } else {
      app.toast(t('capture.hook.testFail'), 'error')
    }
    await refresh()
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  await refresh()
  poll = window.setInterval(refresh, 2000)
})
onBeforeUnmount(() => window.clearInterval(poll))
</script>

<template>
  <section class="framed mt-4 px-3.5 py-2.5">
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
      <span class="kicker">{{ t('capture.hook.title') }}</span>

      <div class="seg">
        <button
          v-for="item in TOOLS"
          :key="item.name"
          type="button"
          class="seg-opt"
          :aria-pressed="tool === item.name"
          @click="tool = item.name"
        >
          {{ item.label }}
        </button>
      </div>

      <span class="inline-flex items-center gap-1.5 type-meta text-ink-70">
        <i
          class="size-1.5 shrink-0 rounded-full"
          :class="
            state === 'connected'
              ? 'bg-accent'
              : state === 'connecting'
                ? 'bg-ink-35'
                : 'border border-divider'
          "
          aria-hidden="true"
        />
        {{ t(STATE_KEY[state]) }}
      </span>

      <span
        v-if="state === 'connected' && current?.last_text"
        class="type-meta min-w-0 text-ink-70"
      >
        {{ t('capture.hook.lastHeard') }}「<span
          class="jp inline-block max-w-64 truncate align-bottom"
          >{{ current.last_text }}</span
        >」<template v-if="current?.last_text_at">
          · {{ relSeconds(current.last_text_at) }}</template
        >
      </span>

      <span class="ml-auto flex flex-wrap items-center gap-x-3 gap-y-1">
        <button v-if="state === 'connected'" class="btn-quiet" :disabled="busy" @click="disconnect">
          {{ t('capture.hook.disconnect') }}
        </button>
        <button v-else class="btn-quiet" :disabled="busy" @click="connect()">
          {{ t('capture.hook.connect') }}
        </button>
        <button class="btn-quiet" :disabled="busy" @click="test">
          {{ t('capture.hook.test') }}
        </button>
        <button
          class="btn-quiet"
          :aria-expanded="showAdvanced"
          @click="showAdvanced = !showAdvanced"
        >
          {{ t('capture.hook.advanced') }}
        </button>
      </span>
    </div>

    <p v-if="state !== 'connected'" class="mt-2 mb-0 type-micro leading-relaxed text-ink-70">
      <template v-if="tool === 'textractor'">
        {{ t('capture.hook.helpTextractor') }}
        <a class="underline" :href="TEXTTRACTOR_GUIDE" target="_blank" rel="noreferrer">
          {{ t('capture.hook.helpTextractorLink') }}
        </a>
      </template>
      <template v-else>{{ t('capture.hook.helpOther') }}</template>
    </p>

    <div v-if="showAdvanced" class="mt-2.5 border-t border-divider pt-2.5">
      <label class="field-label" :for="`hook-url-${tool}`">{{ t('capture.hook.address') }}</label>
      <div class="flex gap-2">
        <input
          :id="`hook-url-${tool}`"
          v-model="urlDraft"
          class="input num"
          spellcheck="false"
          @keydown.enter="connect(urlDraft)"
        />
        <button
          class="btn btn-secondary"
          :disabled="busy || !urlDraft.trim()"
          @click="connect(urlDraft)"
        >
          {{ t('capture.hook.saveAndConnect') }}
        </button>
      </div>
      <p class="mt-2 mb-0 type-micro leading-relaxed text-ink-70">
        {{ t('capture.hook.inboundHint') }}
        <code class="num">{{ wsUrl('/ws/hook') }}</code>
      </p>
      <p v-if="current?.error" class="mt-1 mb-0 type-micro text-ink-70">
        {{ t('capture.hook.lastError') }}：<code class="num">{{ current.error }}</code>
      </p>
    </div>
  </section>
</template>
