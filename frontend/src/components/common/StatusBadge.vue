<script setup lang="ts">
import { STATUS_LABEL } from '@/utils/format'

defineProps<{ status: string | null }>()

/** 学习状态：细边框 + 墨色深浅，不用颜色分类。 */
const CLS: Record<string, string> = {
  unknown: 'border-ink text-ink',
  learning: 'border-divider text-ink-70',
  known: 'border-divider text-ink-50',
  ignored: 'border-divider text-ink-35 line-through',
}
</script>

<template>
  <span v-if="status" class="tag border" :class="CLS[status]">{{ STATUS_LABEL[status] }}</span>
</template>
