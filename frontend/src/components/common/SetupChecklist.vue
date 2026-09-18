<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { SetupProgress } from '@/utils/setup'

defineProps<{ progress: SetupProgress }>()
defineEmits<{ dismiss: [] }>()

const STEPS = [
  {
    key: 'dict',
    label: '安装 JMdict 词典',
    hint: '不装的话，收件箱里点词查不到释义。',
    to: '/settings',
  },
  {
    key: 'region',
    label: '框一个采集区域',
    hint: '在作品里框好对话区域，台词会自动进来。',
    to: '/capture',
  },
  {
    key: 'lines',
    label: '接一个台词来源',
    hint: '连一个 Hook 工具，或者导入字幕。',
    to: '/capture',
  },
] as const
</script>

<template>
  <section class="framed px-5 py-4">
    <div class="flex items-baseline justify-between gap-3 border-b border-divider pb-2.5">
      <p class="kicker m-0">第一次使用</p>
      <button class="btn-quiet" @click="$emit('dismiss')">不再显示</button>
    </div>

    <ul class="m-0 flex list-none flex-col p-0">
      <li
        v-for="step in STEPS"
        :key="step.key"
        class="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-rule py-3 last:border-0 last:pb-0"
      >
        <span
          class="font-head type-body"
          :class="progress[step.key] ? 'text-ink-35' : 'text-ink'"
          >{{ step.label }}</span
        >
        <span class="tag tag-state" :class="progress[step.key] ? 'text-ink-35' : 'text-ink'">
          {{ progress[step.key] ? '已完成' : '待完成' }}
        </span>
        <RouterLink
          v-if="!progress[step.key]"
          :to="step.to"
          class="type-meta text-accent no-underline"
          >去处理 →</RouterLink
        >
        <span class="w-full type-micro leading-[1.7] text-ink-35">{{ step.hint }}</span>
      </li>
    </ul>
  </section>
</template>
