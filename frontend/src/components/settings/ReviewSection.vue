<script setup lang="ts">
import { onMounted } from 'vue'
import SettingsSection from './SettingsSection.vue'
import type { Owner } from '@/api/types'
import { useSettings } from '@/composables/useSettings'

const { settings, load, save } = useSettings()
onMounted(load)

function onOwner(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  save({ review_owner_default: (value === 'auto' ? null : value) as Owner | null })
}
</script>

<template>
  <SettingsSection v-if="settings" title="复习">
    <label class="block text-sm" for="owner-default">
      <span class="kicker">新卡默认归属</span>
      <select
        id="owner-default"
        class="input w-auto"
        :value="settings.review_owner_default ?? 'auto'"
        @change="onOwner"
      >
        <option value="auto">自动（注册了手机就归手机，否则归电脑）</option>
        <option value="desktop">电脑</option>
        <option value="mobile">手机</option>
        <option value="any">任意设备</option>
      </select>
    </label>
    <label class="block text-sm" for="retention">
      <span class="kicker">目标记忆保持率 {{ Math.round(settings.desired_retention * 100) }}%</span>
      <input
        id="retention"
        type="range"
        min="0.75"
        max="0.97"
        step="0.01"
        :value="settings.desired_retention"
        class="w-full"
        @change="save({ desired_retention: Number(($event.target as HTMLInputElement).value) })"
      />
      <span class="text-xs text-ink-3">FSRS 参数：越高复习越频繁。默认 90%。</span>
    </label>
  </SettingsSection>
</template>
