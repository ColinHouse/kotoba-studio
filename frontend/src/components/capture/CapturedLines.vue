<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { mediaUrl } from '@/api/client'
import type { Line } from '@/api/types'
import { relTime } from '@/utils/format'

defineProps<{ lines: Line[]; inboxLink: string }>()

const STATUS_TEXT: Record<string, string> = {
  kept: '已确认',
  discarded: '已丢弃',
  inbox: '待整理',
}
</script>

<template>
  <section class="space-y-2">
    <h2 class="font-semibold">
      本次收藏 <span class="text-sm font-normal text-ink-3">{{ lines.length }} 句</span>
    </h2>
    <ul class="space-y-2">
      <li v-for="line in lines" :key="line.id" class="card flex gap-3 p-3">
        <img
          v-if="line.screenshot_path"
          :src="mediaUrl(line.screenshot_path)"
          class="h-14 w-24 shrink-0 rounded-lg border border-line object-cover"
          alt=""
        />
        <div class="min-w-0 flex-1">
          <p class="jp leading-relaxed">{{ line.text }}</p>
          <p class="text-xs text-ink-3">
            {{ line.origin }} · {{ relTime(line.captured_at) }} · {{ STATUS_TEXT[line.status] }}
          </p>
        </div>
      </li>
    </ul>
    <p v-if="!lines.length" class="text-sm text-ink-2">
      收藏的句子会出现在这里；游戏结束后到收件箱统一整理。
    </p>
    <RouterLink v-if="lines.length" :to="inboxLink" class="btn-outline">去收件箱整理 →</RouterLink>
  </section>
</template>
