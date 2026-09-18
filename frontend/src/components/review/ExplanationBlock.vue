<script setup lang="ts">
import { computed } from 'vue'
import type { Explanation } from '@/api/types'

const props = defineProps<{ explanation: Explanation; bare?: boolean }>()

const ROWS: { key: keyof Explanation; label: string }[] = [
  { key: 'meaning_here', label: '这句里' },
  { key: 'form', label: '词形' },
  { key: 'tone', label: '语气' },
  { key: 'needs_context', label: '需上下文' },
  { key: 'daily_usable', label: '日常' },
  { key: 'trap_for_zh', label: '提醒' },
]

const rows = computed(() =>
  ROWS.filter((r) => typeof props.explanation[r.key] === 'string' && props.explanation[r.key]),
)
const confidence = computed(() =>
  typeof props.explanation.confidence === 'number'
    ? `把握 ${Math.round(props.explanation.confidence * 100)}%`
    : null,
)
</script>

<template>
  <div :class="bare ? '' : 'border-t border-rule bg-surface px-6 pt-4 pb-[18px]'">
    <div class="mb-2.5 flex items-baseline justify-between">
      <span class="kicker text-ink-50">AI 语境解释</span>
      <span v-if="confidence" class="num text-[11px] text-ink-70">{{ confidence }}</span>
    </div>
    <dl
      class="m-0 grid grid-cols-[62px_1fr] gap-x-3 gap-y-2 text-[13px] leading-[1.65] text-ink-70"
    >
      <template v-for="row in rows" :key="row.key">
        <dt class="text-right text-[11px] text-ink-70">{{ row.label }}</dt>
        <dd class="m-0">{{ explanation[row.key] }}</dd>
      </template>
    </dl>
  </div>
</template>
