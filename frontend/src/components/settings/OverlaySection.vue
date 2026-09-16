<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SettingsSection from './SettingsSection.vue'
import { api } from '@/api/client'
import type { OverlayStatus, Settings } from '@/api/types'
import { useSettings } from '@/composables/useSettings'
import { useAppStore } from '@/stores/app'

const app = useAppStore()
const { settings, load, save } = useSettings()
const status = ref<OverlayStatus | null>(null)
const draft = ref('')
const busy = ref(false)

/** Mirror the persisted setting, whatever just happened: this is idempotent. */
async function syncOverlay() {
  status.value = settings.value?.overlay_enabled
    ? await api.post<OverlayStatus>('/api/overlay/start')
    : await api.post<OverlayStatus>('/api/overlay/stop')
}

async function apply(patch: Partial<Settings>) {
  if (busy.value) return
  busy.value = true
  try {
    await save(patch)
    draft.value = settings.value?.overlay_hotkey ?? draft.value
    await syncOverlay()
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

async function retry() {
  busy.value = true
  try {
    await syncOverlay()
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

function commitDraft() {
  if (!settings.value || busy.value) return
  const value = draft.value.trim()
  if (!value || value === settings.value.overlay_hotkey) {
    draft.value = settings.value.overlay_hotkey
    return
  }
  apply({ overlay_hotkey: value })
}

onMounted(async () => {
  await load()
  draft.value = settings.value?.overlay_hotkey ?? ''
  try {
    status.value = await api.get<OverlayStatus>('/api/overlay/status')
  } catch (e) {
    app.fail(e)
  }
})
</script>

<template>
  <SettingsSection v-if="settings" title="游戏内覆盖层">
    <p class="m-0 text-xs text-ink-50">
      覆盖层的面板悬在对话框上方，显示当前句的分词；点词看释义，按「收藏这个词」记下它。
      面板以外的区域点击穿透，不会挡住游戏操作。
    </p>
    <p class="mt-1 mb-0 text-xs text-ink-35">
      只在窗口化 / 无边框窗口下可用，独占全屏显示不出来。目前仅支持 Windows（tkinter）。
    </p>

    <label class="mt-3 flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        :checked="settings.overlay_enabled"
        :disabled="busy"
        @change="apply({ overlay_enabled: !settings.overlay_enabled })"
      />
      启用游戏内覆盖层
    </label>

    <label class="mt-2 block text-sm" for="overlay-hotkey">
      <span class="kicker">呼出 / 隐藏快捷键</span>
      <input
        id="overlay-hotkey"
        class="input w-56"
        :value="draft"
        :disabled="busy"
        spellcheck="false"
        @input="draft = ($event.target as HTMLInputElement).value"
        @blur="commitDraft"
        @keydown.enter="commitDraft"
      />
      <span class="text-xs text-ink-3">例如 Ctrl+Shift+O；改动后回车确认。</span>
    </label>

    <p v-if="status" class="mt-2 flex flex-wrap items-center gap-2 text-xs">
      <template v-if="!status.available">
        <span class="text-accent">{{ status.note }}</span>
      </template>
      <template v-else-if="status.running">
        <span class="text-ink-50">
          {{ status.visible ? '面板显示中' : '面板已隐藏' }} ·
          <span class="num">{{ status.hotkey }}</span> 呼出/隐藏
        </span>
      </template>
      <template v-else>
        <span class="text-ink-35">未启用</span>
      </template>
      <span v-if="status.available && status.last_error" class="text-accent">
        · {{ status.last_error }}
      </span>
      <button
        v-if="status.available && settings.overlay_enabled && !status.running"
        class="btn-quiet"
        :disabled="busy"
        @click="retry"
      >
        重试
      </button>
    </p>
  </SettingsSection>
</template>
