<script setup lang="ts">
import { mediaUrl } from '@/api/client'
import type { Line } from '@/api/types'
import { relTime } from '@/utils/format'

defineProps<{ lines: Line[]; selectedId: number | null; emptyHint: string }>()
defineEmits<{ select: [line: Line] }>()
</script>

<template>
  <TransitionGroup tag="ul" name="list" class="relative m-0 flex list-none flex-col p-0">
    <li v-for="line in lines" :key="line.id">
      <button
        type="button"
        class="line-row flex w-full gap-3 border-0 bg-transparent p-3 text-left"
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
            <span
              v-if="line.unknown_count !== null && line.unknown_count > 0"
              class="tag tag-state ml-1.5 align-middle"
              :class="line.unknown_count === 1 ? 'text-ink' : 'text-ink-50'"
            >
              {{ line.unknown_count === 1 ? 'i+1' : `${line.unknown_count} 个生词` }}
            </span>
          </span>
        </span>
      </button>
    </li>
  </TransitionGroup>
  <p v-if="!lines.length" class="m-0 py-4 text-[13px] text-ink-35">{{ emptyHint }}</p>
</template>

<style scoped>
/* 选中的那一行会从描边变成"抬起"的纸，底色与边线都要落下来而不是跳变。 */
.line-row {
  transition:
    background var(--mo-base) var(--ease-paper),
    border-color var(--mo-base) var(--ease-paper);
}
</style>
