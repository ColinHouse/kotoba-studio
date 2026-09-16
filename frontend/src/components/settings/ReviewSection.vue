<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import SettingsSection from './SettingsSection.vue'
import { api } from '@/api/client'
import type { Owner } from '@/api/types'
import { useSettings } from '@/composables/useSettings'
import { useAppStore } from '@/stores/app'

interface OptimizeResult {
  review_count: number
  old_parameters: number[] | null
  new_parameters: number[]
  optimal_retention: number
}

interface OptimizeSnapshot {
  state: 'idle' | 'running' | 'done' | 'error'
  message: string
  result: OptimizeResult | null
}

const app = useAppStore()
const { settings, load, save } = useSettings()
onMounted(load)

const optimize = ref<OptimizeSnapshot | null>(null)
let poll: number | undefined
onBeforeUnmount(() => window.clearInterval(poll))

function onOwner(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  save({ review_owner_default: (value === 'auto' ? null : value) as Owner | null })
}

async function startOptimize() {
  window.clearInterval(poll)
  try {
    optimize.value = await api.post<OptimizeSnapshot>('/api/reviews/optimize')
    if (optimize.value.state === 'running') {
      poll = window.setInterval(async () => {
        try {
          optimize.value = await api.get<OptimizeSnapshot>('/api/reviews/optimize')
          if (optimize.value.state !== 'running') window.clearInterval(poll)
        } catch (e) {
          window.clearInterval(poll)
          app.fail(e)
        }
      }, 2000)
    }
  } catch (e) {
    app.fail(e)
  }
}

function applyParameters() {
  const result = optimize.value?.result
  if (!result) return
  save({
    fsrs_parameters: result.new_parameters,
    fsrs_parameters_previous: settings.value?.fsrs_parameters ?? result.old_parameters,
  })
}

function restorePrevious() {
  const previous = settings.value?.fsrs_parameters_previous
  if (!previous) return
  save({ fsrs_parameters: previous, fsrs_parameters_previous: null })
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

    <div class="space-y-2 border-t border-divider pt-3">
      <p class="kicker m-0">个人化参数</p>
      <p class="text-xs text-ink-50">
        {{
          settings.fsrs_parameters
            ? '已启用你自己的参数（由复习记录拟合）。'
            : '当前使用 FSRS 默认参数；调度复习满 400 条后可用自己的历史拟合。'
        }}
      </p>
      <div class="flex flex-wrap items-center gap-2">
        <button
          class="btn btn-secondary"
          :disabled="optimize?.state === 'running'"
          @click="startOptimize"
        >
          {{ optimize?.state === 'running' ? '优化中…' : '用我的复习记录优化参数' }}
        </button>
        <button v-if="settings.fsrs_parameters_previous" class="btn-quiet" @click="restorePrevious">
          还原上一组参数
        </button>
      </div>
      <p v-if="optimize && optimize.state !== 'idle'" class="m-0 text-xs text-ink-50">
        {{ optimize.message }}
        <template v-if="optimize.result">
          · 复习 {{ optimize.result.review_count }} 条 · 建议保持率
          {{ Math.round(optimize.result.optimal_retention * 100) }}%
        </template>
      </p>
      <div v-if="optimize?.result" class="flex flex-wrap items-center gap-2">
        <button class="btn btn-primary" @click="applyParameters">应用新参数</button>
        <span class="text-xs text-ink-35">只在你确认后写入；旧参数留一份，可随时还原。</span>
      </div>
    </div>
  </SettingsSection>
</template>
