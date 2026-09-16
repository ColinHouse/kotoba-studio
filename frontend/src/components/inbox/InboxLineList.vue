<script setup lang="ts">
import { mediaUrl } from '@/api/client'
import type { Line } from '@/api/types'
import { relTime } from '@/utils/format'

defineProps<{ lines: Line[]; selectedId: number | null; emptyHint: string }>()
defineEmits<{ select: [line: Line] }>()
</script>

<template>
  <ul class="m-0 flex list-none flex-col p-0">
    <li v-for="line in lines" :key="line.id">
      <button
        type="button"
        class="flex w-full gap-3 border-0 bg-transparent p-3 text-left"
        :class="
          selectedId === line.id
            ? 'lifted'
            : 'cursor-pointer border-b border-rule px-3 pt-3.5 pb-[13px] hover:bg-surface/60'
        "
        @click="$emit('select', line)"
      >
        <img
          v-if="line.screenshot_path"
          :src="mediaUrl(line.screenshot_path)"
          class="plate h-[54px] w-24 shrink-0"
          style="border-width: 4px"
          alt=""
        />
        <span class="min-w-0 flex-1">
          <span
            class="jp block text-[15px] leading-[1.85] md:text-[16px]"
            :class="selectedId === line.id ? 'text-ink' : 'text-ink-70'"
            >{{ line.text }}</span
          >
          <span class="num mt-0.5 block text-[11px] text-ink-35">
            {{ relTime(line.captured_at)
            }}<template v-if="line.encounter_count"> · {{ line.encounter_count }} 个词</template>
            <template v-if="line.status === 'kept'"> · 已确认</template>
          </span>
        </span>
      </button>
    </li>
    <li v-if="!lines.length" class="py-4 text-[13px] text-ink-35">{{ emptyHint }}</li>
  </ul>
</template>
