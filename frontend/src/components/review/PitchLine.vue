<script setup lang="ts">
import { computed } from 'vue'
import { pitchLevels, splitMorae } from '@/utils/pitch'

const props = defineProps<{ reading: string; accent: number; label: string }>()

const UNIT = 22
const HIGH = 4
const LOW = 16

const morae = computed(() => splitMorae(props.reading))
const levels = computed(() => pitchLevels(props.reading, props.accent))
const width = computed(() => Math.max(morae.value.length, 1) * UNIT)

/** Horizontal line over every mora, vertical drop where the level changes. */
const segments = computed(() => {
  const out: { x1: number; y1: number; x2: number; y2: number }[] = []
  levels.value.forEach((high, index) => {
    const y = high ? HIGH : LOW
    out.push({ x1: index * UNIT + 2, y1: y, x2: (index + 1) * UNIT - 2, y2: y })
    const next = levels.value[index + 1]
    if (next !== undefined && next !== high) {
      out.push({ x1: (index + 1) * UNIT, y1: y, x2: (index + 1) * UNIT, y2: next ? HIGH : LOW })
    }
  })
  return out
})
</script>

<template>
  <span class="inline-flex flex-col items-center">
    <svg :width="width" :height="20" class="block" aria-hidden="true">
      <line
        v-for="(s, i) in segments"
        :key="i"
        :x1="s.x1"
        :y1="s.y1"
        :x2="s.x2"
        :y2="s.y2"
        stroke="var(--ink)"
        stroke-width="2"
      />
    </svg>
    <span class="jp flex leading-none">
      <span
        v-for="(mora, i) in morae"
        :key="i"
        class="text-center text-[17px]"
        :style="{ width: `${UNIT}px` }"
        >{{ mora }}</span
      >
    </span>
    <span class="tag tag-state mt-1.5">{{ label }}</span>
  </span>
</template>
