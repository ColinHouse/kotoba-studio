<script setup lang="ts">
import type { Explanation } from '@/api/types'
defineProps<{ explanation: Explanation }>()
const rows: { key: keyof Explanation; label: string }[] = [
  { key: 'meaning_here', label: '这句里的意思' },
  { key: 'form', label: '词形' },
  { key: 'tone', label: '语气' },
  { key: 'needs_context', label: '需要上下文' },
  { key: 'daily_usable', label: '日常能否这样说' },
  { key: 'trap_for_zh', label: '给中文母语者的提醒' },
]
</script>

<template>
  <div class="rounded-xl border border-sky/20 bg-sky/5 p-3 text-sm">
    <div class="mb-1 flex items-center justify-between">
      <span class="label text-sky">AI 语境解释</span>
      <span v-if="explanation.confidence !== undefined" class="text-xs text-ink-3">把握 {{ Math.round((explanation.confidence ?? 0) * 100) }}%</span>
    </div>
    <dl class="space-y-1.5">
      <template v-for="row in rows" :key="row.key">
        <div v-if="explanation[row.key]">
          <dt class="text-xs font-semibold text-ink-2">{{ row.label }}</dt>
          <dd class="leading-relaxed">{{ explanation[row.key] }}</dd>
        </div>
      </template>
    </dl>
    <p class="mt-2 text-[11px] text-ink-3">AI 解释与词典释义分开显示；不确定之处以"需要上下文"标出。</p>
  </div>
</template>
