<script setup lang="ts">
import type { CompareResult } from '@/api/types'

defineProps<{
  results: CompareResult[]
  current: string
  running: boolean
  canRun: boolean
}>()

const emit = defineEmits<{
  run: []
  select: [provider: string]
}>()
</script>

<template>
  <section class="framed mt-5 p-4">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="kicker m-0">引擎对比</p>
      <button class="btn btn-secondary" :disabled="!canRun || running" @click="emit('run')">
        {{ running ? '对比中…' : '对比所有引擎' }}
      </button>
    </div>

    <p v-if="running" class="mt-3 text-[13px] text-ink-50">正在对同一区域跑一遍可用引擎…</p>
    <p v-else-if="!results.length" class="mt-3 text-[13px] text-ink-35">
      {{
        canRun
          ? '还没有结果。跑一次，并排看看哪个引擎认得最准。'
          : '先在左侧框选对话框区域，才能对比。'
      }}
    </p>

    <div v-else class="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
      <button
        v-for="row in results"
        :key="row.provider"
        type="button"
        class="framed flex flex-col items-start p-3 text-left"
        :class="row.provider === current ? 'border-accent' : 'hover:border-ink-35'"
        @click="emit('select', row.provider)"
      >
        <span class="flex w-full items-baseline justify-between gap-2">
          <span class="font-head text-[15px]">{{ row.provider }}</span>
          <span class="num text-[11px] text-ink-35">{{ row.ms }} ms</span>
        </span>
        <span v-if="row.error" class="mt-2 text-[12px] text-ink-50">
          识别失败 · {{ row.error }}
        </span>
        <span v-else class="jp mt-2 whitespace-pre-wrap text-[14px] leading-[1.8] text-ink">
          {{ row.text || '（没有识别到文字）' }}
        </span>
        <span v-if="row.provider === current" class="tag tag-fact mt-2">当前默认</span>
      </button>
    </div>
  </section>
</template>
