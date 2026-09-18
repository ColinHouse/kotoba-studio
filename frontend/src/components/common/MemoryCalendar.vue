<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{ days: { date: string; count: number }[]; height?: number }>(),
  { height: 82 },
)

/** 空白日＝可以放心去玩，所以 0 画成一条极细的线而不是留空。 */
const bars = computed(() => {
  const max = Math.max(1, ...props.days.map((d) => d.count))
  return props.days.map((d, i) => ({
    ...d,
    today: i === 0,
    label: String(Number(d.date.slice(8, 10))),
    barHeight: d.count ? Math.max(4, Math.round((d.count / max) * props.height)) : 1,
  }))
})
const total = computed(() => props.days.reduce((n, d) => n + d.count, 0))
defineExpose({ total })
</script>

<template>
  <div>
    <div
      class="flex items-end gap-2 border-b border-divider md:gap-2.5"
      :style="{ height: `${height + 22}px` }"
    >
      <div
        v-for="d in bars"
        :key="d.date"
        class="flex flex-1 flex-col items-center justify-end gap-1.5"
      >
        <span
          class="num type-micro"
          :class="d.today ? 'font-semibold text-accent' : d.count ? 'text-ink' : 'text-ink-70'"
          >{{ d.count || '·' }}</span
        >
        <div
          class="w-full"
          :style="{
            height: `${d.barHeight}px`,
            background: d.count ? (d.today ? 'var(--accent)' : 'transparent') : 'var(--divider)',
            border: d.count && !d.today ? '1px solid var(--accent)' : 'none',
          }"
        />
      </div>
    </div>
    <div class="mt-1.5 flex gap-2 md:gap-2.5">
      <span
        v-for="d in bars"
        :key="d.date"
        class="num flex-1 text-center type-micro"
        :class="d.today ? 'font-semibold text-accent' : 'text-ink-70'"
        >{{ d.label }}</span
      >
    </div>
  </div>
</template>
