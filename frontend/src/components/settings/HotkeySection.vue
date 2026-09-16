<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SettingsSection from './SettingsSection.vue'
import { api } from '@/api/client'
import type { HotkeyStatus, Settings } from '@/api/types'
import { useSettings } from '@/composables/useSettings'
import { useAppStore } from '@/stores/app'

const app = useAppStore()
const { settings, load, save } = useSettings()
const status = ref<HotkeyStatus | null>(null)
const draft = ref('')
const busy = ref(false)

/** Mirror the persisted setting, whatever just happened: this is idempotent. */
async function syncListener() {
  status.value = settings.value?.capture_hotkey_enabled
    ? await api.post<HotkeyStatus>('/api/capture/hotkeys/start')
    : await api.post<HotkeyStatus>('/api/capture/hotkeys/stop')
}

async function apply(patch: Partial<Settings>) {
  if (busy.value) return
  busy.value = true
  try {
    await save(patch)
    draft.value = settings.value?.capture_hotkey ?? draft.value
    await syncListener()
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

async function retry() {
  busy.value = true
  try {
    await syncListener()
  } catch (e) {
    app.fail(e)
  } finally {
    busy.value = false
  }
}

function commitDraft() {
  if (!settings.value || busy.value) return
  const value = draft.value.trim()
  if (!value || value === settings.value.capture_hotkey) {
    draft.value = settings.value.capture_hotkey
    return
  }
  apply({ capture_hotkey: value })
}

onMounted(async () => {
  await load()
  draft.value = settings.value?.capture_hotkey ?? ''
  try {
    status.value = await api.get<HotkeyStatus>('/api/capture/hotkeys/status')
  } catch (e) {
    app.fail(e)
  }
})
</script>

<template>
  <SettingsSection v-if="settings" title="全局快捷键">
    <p class="m-0 text-xs text-ink-50">
      在游戏里按一次就收藏当前句，不用切回窗口。先要有一个对话区域：在采集页框选一次，
      快捷键只认随作品保存的区域。
    </p>

    <label class="mt-3 flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        :checked="settings.capture_hotkey_enabled"
        :disabled="busy"
        @change="apply({ capture_hotkey_enabled: !settings.capture_hotkey_enabled })"
      />
      启用全局快捷键
    </label>

    <label class="mt-2 block text-sm" for="capture-hotkey">
      <span class="kicker">按键组合</span>
      <input
        id="capture-hotkey"
        class="input w-56"
        :value="draft"
        :disabled="busy"
        spellcheck="false"
        @input="draft = ($event.target as HTMLInputElement).value"
        @blur="commitDraft"
        @keydown.enter="commitDraft"
      />
      <span class="text-xs text-ink-3">例如 Ctrl+Shift+S；改动后回车确认。</span>
    </label>

    <p v-if="status" class="mt-2 flex flex-wrap items-center gap-2 text-xs">
      <template v-if="!status.available">
        <span class="text-accent">{{ status.note }}</span>
      </template>
      <template v-else-if="status.running">
        <span class="text-ink-50"
          >正在监听 <span class="num">{{ status.hotkey }}</span> · 已收藏
          <span class="num">{{ status.captured }}</span> 句</span
        >
      </template>
      <template v-else>
        <span class="text-ink-35">未启用</span>
      </template>
      <span v-if="status.available && status.last_error" class="text-accent">
        · {{ status.last_error }}
      </span>
      <button
        v-if="status.available && settings.capture_hotkey_enabled && !status.running"
        class="btn-quiet"
        :disabled="busy"
        @click="retry"
      >
        重试
      </button>
    </p>
  </SettingsSection>
</template>
