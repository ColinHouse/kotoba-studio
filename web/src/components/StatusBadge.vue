<script setup lang="ts">
import { STATUS_LABEL } from '@/utils/format'
defineProps<{ status: string | null }>()
const cls: Record<string, string> = {
  unknown: 'bg-accent/15 text-accent-2',
  learning: 'bg-sky/15 text-sky',
  known: 'bg-matcha/15 text-matcha',
  ignored: 'bg-line text-ink-3 line-through',
}
</script>

<template>
  <span v-if="status" class="chip text-xs" :class="cls[status]">{{ STATUS_LABEL[status] }}</span>
</template>
