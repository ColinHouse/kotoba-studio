<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { CardStats, Line, Session, Source } from '@/api/types'
import { useAppStore } from '@/stores/app'
import { useDeviceStore } from '@/stores/device'
import { relTime } from '@/utils/format'

const app = useAppStore()
const device = useDeviceStore()
const router = useRouter()
const stats = ref<CardStats | null>(null)
const inbox = ref<Line[]>([])
const sources = ref<Source[]>([])
const sessions = ref<Session[]>([])
const queueCount = ref<number | null>(null)

onMounted(async () => {
  try {
    ;[stats.value, inbox.value, sources.value, sessions.value] = await Promise.all([
      api.get<CardStats>('/api/cards/stats'),
      api.get<Line[]>('/api/lines?status=inbox&limit=200'),
      api.get<Source[]>('/api/sources'),
      api.get<Session[]>('/api/sessions?limit=5'),
    ])
    const q = await api.get<{ cards: unknown[] }>(
      `/api/reviews/queue?device_kind=${device.kind}&limit=200`,
    )
    queueCount.value = q.cards.length
  } catch (e) {
    app.fail(e)
  }
})

async function startSession(source: Source) {
  try {
    const s = await api.post<Session>('/api/sessions', { source_id: source.id, mode: 'companion' })
    app.activeSession = s
    router.push(device.kind === 'desktop' ? '/capture' : '/inbox')
  } catch (e) {
    app.fail(e)
  }
}
</script>

<template>
  <div class="mx-auto max-w-5xl space-y-6">
    <header>
      <h1 class="text-2xl font-semibold">今天</h1>
      <p class="text-sm text-ink-2">
        {{
          device.kind === 'desktop'
            ? '桌面端负责采集，手机负责浏览与复习。'
            : '手机端：浏览与复习；采集请在电脑上进行。'
        }}
      </p>
    </header>

    <div class="grid gap-3 sm:grid-cols-3">
      <RouterLink to="/review" class="card p-4 hover:border-accent">
        <span class="label">待复习（本设备）</span>
        <p class="text-3xl font-semibold">{{ queueCount ?? '…' }}</p>
        <p class="text-xs text-ink-3">
          全部到期 {{ stats?.due_now ?? '…' }} · 新卡 {{ stats?.new ?? '…' }}
        </p>
      </RouterLink>
      <RouterLink to="/inbox" class="card p-4 hover:border-accent">
        <span class="label">收件箱待整理</span>
        <p class="text-3xl font-semibold">{{ inbox.length }}</p>
        <p class="text-xs text-ink-3">收藏的句子，确认后生成卡片</p>
      </RouterLink>
      <RouterLink to="/library" class="card p-4 hover:border-accent">
        <span class="label">卡片总数</span>
        <p class="text-3xl font-semibold">{{ stats?.total ?? '…' }}</p>
        <p class="text-xs text-ink-3">
          归属：电脑 {{ stats?.by_owner.desktop ?? 0 }} · 手机 {{ stats?.by_owner.mobile ?? 0 }} ·
          任意 {{ stats?.by_owner.any ?? 0 }}
        </p>
      </RouterLink>
    </div>

    <section
      v-if="app.activeSession"
      class="card flex flex-wrap items-center justify-between gap-3 p-4"
    >
      <div>
        <span class="label">进行中的会话</span>
        <p class="font-semibold">
          {{ app.activeSession.source_title ?? '未指定作品' }}
          <span class="text-sm font-normal text-ink-3"
            >· {{ app.activeSession.line_count }} 句 · 开始于
            {{ relTime(app.activeSession.started_at) }}</span
          >
        </p>
      </div>
      <div class="flex gap-2">
        <RouterLink v-if="device.kind === 'desktop'" to="/capture" class="btn-primary"
          >继续采集</RouterLink
        >
        <RouterLink to="/inbox" class="btn-outline">整理收件箱</RouterLink>
      </div>
    </section>

    <section>
      <div class="mb-2 flex items-center justify-between">
        <h2 class="font-semibold">作品</h2>
        <RouterLink to="/sources" class="text-sm text-accent-2">管理</RouterLink>
      </div>
      <div v-if="sources.length" class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="s in sources.slice(0, 6)"
          :key="s.id"
          class="card flex items-center justify-between p-3"
        >
          <div>
            <p class="font-semibold">{{ s.title }}</p>
            <p class="text-xs text-ink-3">
              {{ s.line_count }} 句 · {{ s.term_count }} 词{{ s.region ? ' · 已设区域' : '' }}
            </p>
          </div>
          <button
            v-if="device.kind === 'desktop'"
            class="btn-ghost text-xs"
            @click="startSession(s)"
          >
            开始会话
          </button>
        </div>
      </div>
      <div v-else class="card p-4 text-sm text-ink-2">
        还没有作品。<RouterLink to="/sources" class="text-accent-2"
          >添加一部 Galgame 或动画</RouterLink
        >，然后开始第一次会话。
      </div>
    </section>

    <section v-if="sessions.length">
      <h2 class="mb-2 font-semibold">最近会话</h2>
      <ul class="card divide-y divide-line">
        <li
          v-for="s in sessions"
          :key="s.id"
          class="flex items-center justify-between px-4 py-2 text-sm"
        >
          <span
            >{{ s.source_title ?? '—' }} · {{ s.line_count }} 句 · {{ relTime(s.started_at) }}</span
          >
          <span class="flex gap-3">
            <RouterLink :to="`/inbox?session=${s.id}`" class="text-accent-2">收件箱</RouterLink>
            <RouterLink :to="`/quiz/${s.id}`" class="text-accent-2">短测</RouterLink>
          </span>
        </li>
      </ul>
    </section>
  </div>
</template>
