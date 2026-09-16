<script setup lang="ts">
import { mediaUrl } from '@/api/client'
import type { Line } from '@/api/types'
import { relTime } from '@/utils/format'

defineProps<{ lines: Line[]; selectedId: number | null; emptyHint: string }>()
defineEmits<{ select: [line: Line] }>()
</script>

<template>
  <ul class="space-y-2">
    <li
      v-for="line in lines"
      :key="line.id"
      class="card cursor-pointer p-3 transition"
      :class="selectedId === line.id ? 'border-accent ring-1 ring-accent' : 'hover:border-ink-3'"
      @click="$emit('select', line)"
    >
      <div class="flex gap-3">
        <img
          v-if="line.screenshot_path"
          :src="mediaUrl(line.screenshot_path)"
          class="h-12 w-20 shrink-0 rounded-md border border-line object-cover"
          alt=""
        />
        <div class="min-w-0 flex-1">
          <p class="jp leading-relaxed">{{ line.text }}</p>
          <p class="text-xs text-ink-3">
            {{ relTime(line.captured_at)
            }}<span v-if="line.encounter_count"> · {{ line.encounter_count }} 个词</span>
          </p>
        </div>
      </div>
    </li>
    <li v-if="!lines.length" class="text-sm text-ink-2">{{ emptyHint }}</li>
  </ul>
</template>
