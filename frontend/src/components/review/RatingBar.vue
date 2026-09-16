<script setup lang="ts">
import { humanInterval } from '@/utils/format'
defineProps<{ preview: Record<'again' | 'hard' | 'good' | 'easy', string>; disabled?: boolean }>()
const emit = defineEmits<{ rate: [rating: 1 | 2 | 3 | 4] }>()
const buttons: { rating: 1 | 2 | 3 | 4; key: 'again' | 'hard' | 'good' | 'easy'; label: string; cls: string }[] = [
  { rating: 1, key: 'again', label: '忘了', cls: 'bg-red-500/90 text-white' },
  { rating: 2, key: 'hard', label: '困难', cls: 'bg-accent text-white' },
  { rating: 3, key: 'good', label: '记得', cls: 'bg-matcha text-white' },
  { rating: 4, key: 'easy', label: '简单', cls: 'bg-sky text-white' },
]
</script>

<template>
  <div class="grid grid-cols-4 gap-2">
    <button
      v-for="b in buttons"
      :key="b.rating"
      type="button"
      class="btn flex-col py-2 leading-tight"
      :class="b.cls"
      :disabled="disabled"
      @click="emit('rate', b.rating)"
    >
      <span>{{ b.label }}</span>
      <span class="text-[11px] opacity-80">{{ humanInterval(preview[b.key]) }} · {{ b.rating }}</span>
    </button>
  </div>
</template>
