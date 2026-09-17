<script setup lang="ts">
import type { ReaderBlock } from '@/api/types'
import { lineInk } from '@/utils/reader'

defineProps<{ blocks: ReaderBlock[]; activeLineId: number | null }>()
defineEmits<{ select: [block: ReaderBlock] }>()
</script>

<template>
  <div class="h-full overflow-y-auto px-3 py-3 md:px-5">
    <ul class="m-0 flex list-none flex-col gap-2 p-0">
      <li v-for="block in blocks" :key="block.line_id">
        <button
          type="button"
          :class="[lineInk(block), block.line_id === activeLineId && 'reader-line-active']"
          @click="$emit('select', block)"
        >
          <span class="jp">{{ block.text }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>
