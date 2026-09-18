<script setup lang="ts">
import { humanInterval } from '@/utils/format'

defineProps<{
  preview: Record<'again' | 'hard' | 'good' | 'easy', string>
  disabled?: boolean
}>()
const emit = defineEmits<{ rate: [rating: 1 | 2 | 3 | 4] }>()

/** 正划笔数＝键盘数字；底色沿金色梯度递进，不用红绿。 */
const BUTTONS = [
  { rating: 1, key: 'again', label: '忘了', cls: 'rate-1' },
  { rating: 2, key: 'hard', label: '困难', cls: 'rate-2' },
  { rating: 3, key: 'good', label: '记得', cls: 'rate-3' },
  { rating: 4, key: 'easy', label: '简单', cls: 'rate-4' },
] as const
</script>

<template>
  <div class="grid grid-cols-4 gap-2">
    <button
      v-for="b in BUTTONS"
      :key="b.rating"
      type="button"
      class="rate"
      :class="b.cls"
      :disabled="disabled"
      :title="`${b.label}（键盘 ${b.rating}）`"
      @click="emit('rate', b.rating)"
    >
      <span class="flex h-[11px] items-end gap-0.5">
        <i v-for="n in b.rating" :key="n" class="block h-[11px] w-px bg-current" />
      </span>
      <span class="font-head type-body leading-none md:text-[17px]">{{ b.label }}</span>
      <span class="num type-micro text-ink-50">{{ humanInterval(preview[b.key]) }}</span>
    </button>
  </div>
</template>

<style scoped>
.rate {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 10px 0 9px;
  border: 1px solid var(--divider);
  border-radius: var(--radius-ui);
  background: transparent;
  cursor: pointer;
  transition:
    background var(--mo-quick) var(--ease-soft),
    filter var(--mo-quick) var(--ease-soft),
    transform var(--mo-quick) var(--ease-soft);
  -webkit-tap-highlight-color: transparent;
}
.rate:active:not(:disabled) {
  transform: translateY(0.5px);
  filter: brightness(0.92);
}
.rate:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.rate-1 {
  color: var(--ink-50);
}
.rate-2 {
  background: var(--accent-100);
  color: var(--ink-70);
}
.rate-3 {
  background: var(--accent-200);
  color: var(--ink);
}
.rate-4 {
  background: var(--accent-300);
  border-color: var(--accent);
  color: var(--accent-800);
}
</style>
