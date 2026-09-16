<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SettingsSection from './SettingsSection.vue'
import { api } from '@/api/client'
import type { AiUsage } from '@/api/types'
import { useSettings } from '@/composables/useSettings'
import { useAppStore } from '@/stores/app'

interface KeyStatus {
  provider: string
  configured: boolean
  source: string
}
type Preset = { base_url: string; model: string }

const app = useAppStore()
const { settings, load, save } = useSettings()
const presets = ref<Record<string, Preset>>({})
const usage = ref<AiUsage | null>(null)
const keyStatus = ref<KeyStatus | null>(null)
const apiKey = ref('')
const saving = ref(false)

onMounted(async () => {
  await load()
  try {
    ;[usage.value, keyStatus.value] = await Promise.all([
      api.get<AiUsage>('/api/ai/usage'),
      api.get<KeyStatus>('/api/settings/ai-key'),
    ])
    presets.value = (await api.get<{ presets: Record<string, Preset> }>('/api/ai/presets')).presets
  } catch (e) {
    app.fail(e)
  }
})

function applyPreset(name: string) {
  const preset = presets.value[name]
  if (preset) save({ ai_provider: name, ai_base_url: preset.base_url, ai_model: preset.model })
}

async function saveKey() {
  if (!apiKey.value.trim() || !settings.value) return
  saving.value = true
  try {
    keyStatus.value = await api.put<KeyStatus>('/api/settings/ai-key', {
      provider: settings.value.ai_provider,
      key: apiKey.value,
    })
    apiKey.value = ''
    app.toast('API Key 已存入系统凭据', 'success')
  } catch (e) {
    app.fail(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <SettingsSection
    v-if="settings"
    title="AI 解释（可选）"
    hint="收藏、查词和复习都不依赖 AI；出错也不会影响收藏。"
  >
    <div class="flex flex-wrap gap-2">
      <button
        v-for="(preset, name) in presets"
        :key="name"
        class="btn-quiet"
        :class="{ 'ring-2 ring-accent': settings.ai_provider === name }"
        @click="applyPreset(name as string)"
      >
        {{ name }}
      </button>
    </div>
    <div class="grid gap-2 sm:grid-cols-2">
      <label class="text-sm" for="ai-base-url">
        <span class="kicker">Base URL</span>
        <input
          id="ai-base-url"
          :value="settings.ai_base_url"
          class="input"
          @change="save({ ai_base_url: ($event.target as HTMLInputElement).value })"
        />
      </label>
      <label class="text-sm" for="ai-model">
        <span class="kicker">模型</span>
        <input
          id="ai-model"
          :value="settings.ai_model"
          class="input"
          @change="save({ ai_model: ($event.target as HTMLInputElement).value })"
        />
      </label>
    </div>
    <div class="flex flex-wrap gap-2">
      <input
        id="ai-key"
        v-model="apiKey"
        type="password"
        class="input flex-1"
        :placeholder="
          keyStatus?.configured
            ? `已配置（${keyStatus.source}），输入新 Key 可替换`
            : '粘贴 API Key（存入系统钥匙串，不写进数据库）'
        "
      />
      <button class="btn btn-secondary" :disabled="saving || !apiKey" @click="saveKey">
        保存 Key
      </button>
    </div>
    <p v-if="usage" class="text-xs text-ink-3">
      已调用 {{ usage.calls }} 次（失败 {{ usage.failed }}）· 估算费用 ${{
        usage.cost_estimate_usd.toFixed(4)
      }}
      · 只发送目标词、当前句和之前 ≤3 句，不发送后续剧情。
    </p>
  </SettingsSection>
</template>
