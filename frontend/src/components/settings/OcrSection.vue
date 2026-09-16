<script setup lang="ts">
import { onMounted, ref } from 'vue'
import SettingsSection from './SettingsSection.vue'
import { api } from '@/api/client'
import type { Provider } from '@/api/types'
import { useSettings } from '@/composables/useSettings'
import { useAppStore } from '@/stores/app'

const app = useAppStore()
const { settings, load, save } = useSettings()
const providers = ref<Provider[]>([])

onMounted(async () => {
  await load()
  try {
    providers.value = await api.get<Provider[]>('/api/capture/providers')
  } catch (e) {
    app.fail(e)
  }
})
</script>

<template>
  <SettingsSection title="OCR 引擎">
    <ul class="text-sm">
      <li v-for="p in providers" :key="p.name" class="flex flex-wrap items-center gap-2 py-1">
        <span
          class="h-2 w-2 shrink-0 rounded-full"
          :class="p.available ? 'bg-matcha' : 'bg-line'"
        />
        <span class="font-mono">{{ p.name }}</span>
        <span class="text-ink-2">{{ p.note }}</span>
        <span v-if="p.recommended" class="tag tag-fact">推荐</span>
      </li>
    </ul>
    <label v-if="settings" class="block text-sm" for="ocr-provider">
      <span class="kicker">默认引擎</span>
      <select
        id="ocr-provider"
        class="input w-auto"
        :value="settings.ocr_provider"
        @change="save({ ocr_provider: ($event.target as HTMLSelectElement).value })"
      >
        <option value="auto">自动</option>
        <option v-for="p in providers" :key="p.name" :value="p.name">{{ p.name }}</option>
      </select>
    </label>
  </SettingsSection>
</template>
